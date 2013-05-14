#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import datetime
import operator
from abc import ABCMeta, abstractmethod

from ZODB.interfaces import IConnection

from nti.utils._compat import aq_base

from nti.appserver.traversal import find_interface
from nti.appserver._util import uncached_in_response
from nti.appserver import interfaces as app_interfaces
from nti.appserver._view_utils import AbstractAuthenticatedView
from nti.appserver._view_utils import ModeledContentUploadRequestUtilsMixin

from nti.appserver.dataserver_pyramid_views import _GenericGetView as GenericGetView
from nti.appserver.ugd_edit_views import UGDPutView
from nti.appserver.ugd_edit_views import UGDDeleteView
from nti.appserver.ugd_query_views import _UGDView as UGDQueryView

from nti.appserver.ugd_feed_views import AbstractFeedView

from nti.dataserver import interfaces as nti_interfaces
from nti.appserver import interfaces as app_interfaces

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import ObjectSharingModifiedEvent

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry
from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic
from nti.dataserver.contenttypes.forums.post import PersonalBlogEntryPost
from nti.dataserver.contenttypes.forums.post import PersonalBlogComment
from nti.dataserver.contenttypes.forums.post import Post
from nti.dataserver.contenttypes.forums.post import CommunityHeadlinePost
from nti.dataserver.contenttypes.forums.post import GeneralForumComment
from nti.dataserver.contenttypes.forums.forum import CommunityForum


from nti.externalization.interfaces import StandardExternalFields

from pyramid.view import view_config
from pyramid.view import view_defaults # NOTE: Only usable on classes

from zope.container.interfaces import INameChooser
from zope.container.contained import dispatchToSublocations
from zope import component
from zope import interface
from zope import lifecycleevent
from zope.event import notify

from . import VIEW_PUBLISH
from . import VIEW_UNPUBLISH
from . import VIEW_CONTENTS

@interface.implementer(app_interfaces.IContainerCollection)
@component.adapter(app_interfaces.IUserWorkspace)
class _UserBlogCollection(object):
	"""
	Turns a User into a ICollection of data for their blog entries (individual containers).
	"""

	name = 'Blog'
	__name__ = name
	__parent__ = None

	def __init__( self, user_workspace ):
		self.__parent__ = user_workspace

	@property
	def container(self):
		return frm_interfaces.IPersonalBlog( self.__parent__.user ).values() # ?

	@property
	def accepts(self):
		return (PersonalBlogEntryPost.mimeType, Post.mimeType)

@interface.implementer(app_interfaces.IContainerCollection)
@component.adapter(app_interfaces.IUserWorkspace)
def _UserBlogCollectionFactory(workspace):
	blog = frm_interfaces.IPersonalBlog( workspace.user, None )
	if blog is not None:
		return _UserBlogCollection( workspace )

class _AbstractIPostPOSTView(AbstractAuthenticatedView,ModeledContentUploadRequestUtilsMixin):
	""" HTTP says POST creates a NEW entity under the Request-URI """
	# Therefore our context is a container, and we should respond created.

	_constraint = frm_interfaces.IPost.providedBy

	_override_content_type = None
	#: Set to a non-empty sequence to require one of a particular type. The `_override_content_type`
	#: is only applied if the incoming type is in the sequence; you must have a valid
	#: `_constraint` in that case to protect against other incoming types.
	#: Set to None to always use the _override_content_type (forcing parsing the incoming data
	#: as that type no matter what)
	_allowed_content_types = ()

	def _transformContentType( self, contenttype ):
		if self._override_content_type:
			if self._allowed_content_types is None:
				contenttype = self._override_content_type
			elif contenttype in self._allowed_content_types:
				contenttype = self._override_content_type
		return contenttype

	def _read_incoming_post( self ):
		# Note the similarity to ugd_edit_views
		creator = self.getRemoteUser()
		externalValue = self.readInput()
		datatype = self.findContentType( externalValue )
		tx_datatype = self._transformContentType( datatype )
		if tx_datatype is not datatype:
			datatype = tx_datatype
			if '/' in datatype:
				externalValue[StandardExternalFields.MIMETYPE] = datatype
			else:
				externalValue[StandardExternalFields.CLASS] = datatype

		containedObject = self.createAndCheckContentObject( creator, datatype, externalValue, creator, self._constraint )
		containedObject.creator = creator

		# The process of updating may need to index and create KeyReferences
		# so we need to have a jar. We don't have a parent to inherit from just yet
		# (If we try to set the wrong one, it messes with some events and some
		# KeyError detection in the containers)
		#containedObject.__parent__ = owner
		owner_jar = IConnection( self.request.context )
		if owner_jar and getattr( containedObject, '_p_jar', self) is None:
			owner_jar.add( containedObject )

		# Update the object, but don't fire any modified events. We don't know
		# if we'll keep this object yet, and we haven't fired a created event
		self.updateContentObject( containedObject, externalValue, set_id=False, notify=False )
		# Which just verified the validity of the title.

		return containedObject, externalValue

class _AbstractForumPostView(_AbstractIPostPOSTView):
	""" Given an incoming IPost, creates a new container in the context. """

	_allowed_content_types = ('Post', Post.mimeType, 'Posts' )
	_factory = None

	def _get_topic_creator( self ):
		return self.getRemoteUser()

	def _do_call( self ):
		forum = self.request.context
		topic_post, external_value = self._read_incoming_post()

		# Now the topic
		topic = self._factory()
		topic.creator = self._get_topic_creator()

		# Business rule: titles of the personal blog entry match the post
		topic.title = topic_post.title
		topic.description = external_value.get( 'description', topic.title )

		# For these, the name matters. We want it to be as pretty as we can get
		# TODO: We probably need to register an IReservedNames that forbids
		# _VIEW_CONTENTS and maybe some other stuff
		name = INameChooser( forum ).chooseName( topic.title, topic )

		lifecycleevent.created( topic )
		forum[name] = topic # Now store the topic and fire lifecycleevent.added
		assert topic.id == name
		assert topic.containerId == forum.NTIID

		if interface.providedBy( topic ).get('headline'):
			# not all containers have headlines; those that don't simply use
			# the incoming post as a template
			topic_post.__parent__ = topic # must set __parent__ first for acquisition to work

			topic_post.creator = topic.creator

			# In order to meet the validity requirements, we must work from the root down,
			# only assigning the sublocation once the parent location is fully valid
			# (otherwise we get schema validation errors)...
			topic.headline = topic_post

			# ...this means, however, that the initial ObjectAddedEvent did not get fired
			# for the headline post (since it just now became a sublocation) so we must do
			# it manually
			lifecycleevent.created( topic_post )
			lifecycleevent.added( topic_post )

		# Respond with the pretty location of the object, within the blog
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_path( topic )

		return topic

_view_defaults = dict(  route_name='objects.generic.traversal',
						renderer='rest' )
_c_view_defaults = _view_defaults.copy()
_c_view_defaults.update( permission=nauth.ACT_CREATE,
						 request_method='POST' )
_r_view_defaults = _view_defaults.copy()
_r_view_defaults.update( permission=nauth.ACT_READ,
						 request_method='GET' )
_d_view_defaults = _view_defaults.copy()
_d_view_defaults.update( permission=nauth.ACT_DELETE,
						 request_method='DELETE' )

# We allow POSTing comments/topics/forums to the actual objects, and also
# to the /contents sub-URL (ignoring anything subpath after it)
# This lets a HTTP client do a better job of caching, by
# auto-invalidating after its own comment creation
# (Of course this has the side-problem of not invalidating
# a cache of the topic object itself...)

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.IPersonalBlog,
				**_c_view_defaults)
class PersonalBlogPostView(_AbstractForumPostView):
	""" Given an incoming IPost, creates a new topic in the blog """

	_constraint = frm_interfaces.IPersonalBlogEntryPost.providedBy
	_override_content_type = PersonalBlogEntryPost.mimeType
	_factory = PersonalBlogEntry

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.ICommunityBoard,
				**_c_view_defaults)
class CommunityBoardPostView(_AbstractForumPostView):
	""" Given an incoming IPost, creates a new forum in the community board """
	# Still read the incoming IPost-like thing, but we discard it since our "topic" (aka forum)
	# does not have a headline
	_factory = CommunityForum
	#: We always override the incoming content type and parse simply as an IPost.
	#: All we care about is topic and description.
	_allowed_content_types = None
	_override_content_type = Post.mimeType

	def _get_topic_creator( self ):
		return self.request.context.creator # the community

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.ICommunityForum,
				**_c_view_defaults )
class CommunityForumPostView(_AbstractForumPostView):
	""" Given an incoming IPost, creates a new topic in the community forum """

	_constraint = frm_interfaces.ICommunityHeadlinePost.providedBy
	_override_content_type = CommunityHeadlinePost.mimeType
	_factory = CommunityHeadlineTopic


class _AbstractTopicPostView(_AbstractIPostPOSTView):

	_allowed_content_types = ('Post', Post.mimeType, 'Posts')

	def _do_call( self ):
		incoming_post, _ = self._read_incoming_post()

		topic = self.request.context

		# The actual name of these isn't tremendously important
		name = topic.generateId( prefix='comment' )

		lifecycleevent.created( incoming_post )
		# incoming_post.id and containerId are set automatically when it is added
		# to the container (but note that the created event did not have them)
		topic[name] = incoming_post # Now store the topic and fire IObjectAddedEvent (subtype of IObjectModifiedEvent)

		# Respond with the pretty location of the object
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_path( incoming_post )

		return incoming_post

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.ICommunityHeadlineTopic,
				**_c_view_defaults )
class CommunityHeadlineTopicPostView(_AbstractTopicPostView):

	_constraint = frm_interfaces.IGeneralForumComment.providedBy
	_override_content_type = GeneralForumComment.mimeType

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=frm_interfaces.IPersonalBlogEntry,
				**_c_view_defaults )
class PersonalBlogEntryPostView(_AbstractTopicPostView):

	_constraint = frm_interfaces.IPersonalBlogComment.providedBy
	_override_content_type = PersonalBlogComment.mimeType


@view_config( context=frm_interfaces.IHeadlineTopic )
@view_config( context=frm_interfaces.IForum )
@view_config( context=frm_interfaces.ICommunityForum )
@view_config( context=frm_interfaces.ICommunityBoard )
@view_config( context=frm_interfaces.IPersonalBlog ) # need to re-list this one
@view_config( context=frm_interfaces.IPersonalBlogEntry ) # need to re-list this one
@view_config( context=frm_interfaces.IPersonalBlogComment ) # need to re-list this one
@view_config( context=frm_interfaces.IPersonalBlogEntryPost ) # need to re-list this one
@view_config( context=frm_interfaces.ICommunityHeadlineTopic ) # need to re-list
@view_config( context=frm_interfaces.ICommunityHeadlinePost ) # need to re-list
@view_config( context=frm_interfaces.IGeneralForumComment ) # need to re-list
@view_config( context=frm_interfaces.IPost )
@view_defaults( **_r_view_defaults )
class ForumGetView(GenericGetView):
	""" Support for simply returning the blog item """


@view_config( context=frm_interfaces.IBoard )
@view_config( context=frm_interfaces.ICommunityHeadlineTopic )
@view_config( context=frm_interfaces.IPersonalBlogEntry )
@view_defaults( name=VIEW_CONTENTS,
				**_r_view_defaults )
class ForumsContainerContentsGetView(UGDQueryView):
	""" The /contents view for the forum objects we are using.

	The contents fully support the same sorting and paging parameters as
	the UGD views. """


	def __init__( self, request ):
		self.request = request
		super(ForumsContainerContentsGetView,self).__init__( request, the_user=self, the_ntiid=self.request.context.__name__ )

		# The user/community is really the 'owner' of the data
		self.user = find_interface(  self.request.context, nti_interfaces.IEntity )

		if frm_interfaces.IBoard.providedBy( self.request.context ):
			self.result_iface = app_interfaces.ILongerCachedUGDExternalCollection

		# If we were invoked with a subpath, then it must be the tokenized
		# version so we can allow for good caching, as we will change the token
		# when the data changes.
		# XXX Except the browser application sometimes does and sometimes does
		# not make a fresh request for the /contents. It seems to be based on
		# where you're coming from. It's even possible for it to get in the state
		# that the order of your page views shows two different sets of contents
		# for the same forum.
		# XXX I think part of this may be because some parent containers (Forum) do not
		# get modification times updated on them when grandchildren change. In the
		# immediate term, we do this just with the topics, where we know one level
		# works.
		# XXX It seems that the "parent" objects can be cached at the application level, meaning
		# that the application never sees the updated contents URLs, making it impossible
		# to HTTP cache them.
		if False and frm_interfaces.IHeadlineTopic.providedBy( request.context ) and self.request.subpath:
			self.result_iface = app_interfaces.IETagCachedUGDExternalCollection

	def __call__( self ):
		try:
			# See if we are something that maintains reliable modification dates
			# including our children.
			# (only ITopic is registered for this). If so, then we want to use
			# this fact when we create the ultimate return ETag.
			# We also want to bail now with 304 Not Modified if we can
			app_interfaces.IPreRenderResponseCacheController( self.request.context )( self.request.context, {'request': self.request} )
			self.result_iface = app_interfaces.IUseTheRequestContextUGDExternalCollection
		except TypeError:
			pass

		return super(ForumsContainerContentsGetView,self).__call__()

	def getObjectsForId( self, *args ):
		return (self.request.context,)


@view_config( context=frm_interfaces.ICommunityBoard )
class CommunityBoardContentsGetView(ForumsContainerContentsGetView):

	def __init__( self, request ):
		# Make sure that if it's going to have a default, it does
		frm_interfaces.ICommunityForum( request.context.creator, None )
		super(CommunityBoardContentsGetView,self).__init__( request )

	def _update_last_modified_after_sort(self, objects, result ):
		# We need to somehow take the modification date of the children
		# into account since we aren't tracking that directly (it doesn't
		# propagate upward). TODO: This should be cached somewhere
		board = objects[0]
		forumLastMod = max( (x.lastModified for x in board.itervalues()) )
		lastMod = max(result.lastModified, forumLastMod)
		result.lastModified = lastMod
		super(CommunityBoardContentsGetView,self)._update_last_modified_after_sort( objects, result )




@view_config( context=frm_interfaces.IForum )
@view_config( context=frm_interfaces.ICommunityForum )
@view_config( context=frm_interfaces.IPersonalBlog )
@view_defaults( name=VIEW_CONTENTS,
				**_r_view_defaults )
class ForumContentsGetView(ForumsContainerContentsGetView):
	"""
	Adds support for sorting by ``NewestDescendantCreatedTime`` of the individual topics,
	and makes sure that the Last Modified time reflects that value.
	"""

	SORT_KEYS = ForumsContainerContentsGetView.SORT_KEYS.copy()
	SORT_KEYS['NewestDescendantCreatedTime'] = operator.attrgetter('NewestDescendantCreatedTime')

	def __call__( self ):
		result = super(ForumContentsGetView,self).__call__()

		if self.request.context:
			# Sigh. Loading all the objects.
			# TODO: We are doing this even for comments during the RSS/Atom feed process, which
			# is weird.
			# NOTE: Using the key= argument fails because it masks AttributeErrors and results in
			# heterogenous comparisons
			newest_time = max( (getattr(x, 'NewestDescendantCreatedTime', 0) for x in self.request.context.values()) )
			newest_time = max( result.lastModified, newest_time )
			result.lastModified = newest_time
			result['Last Modified'] = newest_time
		return result

@view_config( context=frm_interfaces.IHeadlineTopic,
			  name='feed.atom' )
@view_config( context=frm_interfaces.IHeadlineTopic,
			  name='feed.rss' )
@view_config( context=frm_interfaces.IForum,
			  name='feed.atom' )
@view_config( context=frm_interfaces.IForum,
			  name='feed.rss' )
@view_defaults( http_cache=datetime.timedelta(hours=1),
				**_r_view_defaults )
class ForumContentsFeedView(AbstractFeedView):
	_data_callable_factory = ForumContentsGetView

	def _feed_title( self ):
		return self.request.context.title

	def _object_and_creator( self, ipost_or_itopic ):
		title = ipost_or_itopic.title
		# The object to render is either the 'story' (blog text) or the post itself
		data_object = ipost_or_itopic.headline if frm_interfaces.IHeadlineTopic.providedBy( ipost_or_itopic ) else ipost_or_itopic
		return data_object, ipost_or_itopic.creator, title, ipost_or_itopic.tags

@view_config( context=frm_interfaces.IHeadlinePost )
@view_config( context=frm_interfaces.IPersonalBlogEntry )
@view_config( context=frm_interfaces.IPersonalBlogEntryPost )
@view_config( context=frm_interfaces.IPersonalBlogComment )
@view_config( context=frm_interfaces.IGeneralForumComment )
@view_config( context=frm_interfaces.ICommunityHeadlinePost )
@view_config( context=frm_interfaces.ICommunityForum )
@view_defaults( permission=nauth.ACT_UPDATE,
				request_method='PUT',
				**_view_defaults)
class ForumObjectPutView(UGDPutView):
	""" Editing an existing forum post, etc """
	# Exists entirely for registration sake.

@view_config( context=frm_interfaces.ICommunityHeadlineTopic )
@view_config( context=frm_interfaces.IPersonalBlogEntry )
@view_defaults(**_d_view_defaults)
class HeadlineTopicDeleteView(UGDDeleteView):
	""" Deleting an existing topic """

	## Deleting an IPersonalBlogEntry winds up in users.users.py:user_willRemoveIntIdForContainedObject,
	## thus posting the usual activitystream DELETE notifications

	def _do_delete_object( self, theObject ):
		# Delete from enclosing container
		del aq_base(theObject.__parent__)[theObject.__name__]
		return theObject

@view_config( context=frm_interfaces.ICommunityForum )
@view_defaults(**_d_view_defaults)
class ForumDeleteView(UGDDeleteView):
	""" Deleting an existing forum """

	def _do_delete_object( self, theObject ):
		# Standard delete from enclosing container. This
		# dispatches to all the sublocations and thus removes
		# the comments, etc, and into the activity streams
		del aq_base(theObject.__parent__)[theObject.__name__]
		return theObject

@view_config(context=frm_interfaces.IGeneralForumComment)
@view_config(context=frm_interfaces.IPersonalBlogComment)
@view_defaults(**_d_view_defaults)
class CommentDeleteView(UGDDeleteView):
	""" Deleting an existing forum comment.

	This is somewhat unusual as we leave an object behind to mark
	the object as deleted (in fact, we leave the original object
	behind to preserve its timestamps and IDs) we only apply a marker and
	clear the body.
	"""

	def _do_delete_object( self, theObject ):
		deleting = aq_base(theObject)
		interface.alsoProvides( deleting, app_interfaces.IDeletedObjectPlaceholder )

		# TODO: Events need to fire to unindex, once we figure
		# out what those are?
		# We are I18N as externalization time
		deleting.title = None
		deleting.body = None
		deleting.tags = ()
		# Because we are not actually removing it, no IObjectRemoved events fire
		# but we do want to sent a modified event to be sure that timestamps, etc,
		# get updated. This also triggers removing from the user's Activity
		notify( lifecycleevent.ObjectModifiedEvent( deleting ) )
		return theObject


@component.adapter(frm_interfaces.IPost, lifecycleevent.IObjectModifiedEvent)
def match_title_of_post_to_blog( post, event ):
	"When the main story of a story topic (blog post) is modified, match the titles"

	if frm_interfaces.IHeadlineTopic.providedBy( post.__parent__ ) and aq_base(post) is aq_base(post.__parent__.headline) and post.title != post.__parent__.title:
		post.__parent__.title = post.title
	return


### Publishing workflow


class _AbstractPublishingView(object):
	__metaclass__ = ABCMeta

	_iface = nti_interfaces.IDefaultPublished

	def __init__( self, request ):
		self.request = request

	@abstractmethod
	def _do_provide(self, topic):
		"""This method is responsible for firing any ObjectSharingModifiedEvents needed."""
		# Which is done by the topic object's publish/unpublish method
		raise NotImplementedError() # pragma: no cover
	@abstractmethod
	def _test_provides(self, topic):
		raise NotImplementedError() # pragma: no cover

	def __call__(self):
		request = self.request
		topic = request.context
		if self._test_provides( topic ):
			self._do_provide( topic )

		request.response.location = request.resource_path( topic )
		return uncached_in_response( topic )

@view_config( context=frm_interfaces.ICommunityHeadlineTopic )
@view_config( context=frm_interfaces.IPersonalBlogEntry )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='POST',
				name=VIEW_PUBLISH )
class _PublishView(_AbstractPublishingView):
	def _do_provide( self, topic ):
		topic.publish()
	def _test_provides( self, topic ):
		return not nti_interfaces.IDefaultPublished.providedBy( topic )

@view_config( context=frm_interfaces.ICommunityHeadlineTopic )
@view_config( context=frm_interfaces.IPersonalBlogEntry )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='POST',
				name=VIEW_UNPUBLISH )
class _UnpublishView(_AbstractPublishingView):
	def _do_provide( self, topic ):
		topic.unpublish()
	def _test_provides( self, topic ):
		return nti_interfaces.IDefaultPublished.providedBy( topic )


### Events
## TODO: Under heavy construction
###


from nti.dataserver.liking import FAVR_CAT_NAME

def temp_store_favorite_object( modified_object, event ):
	if event.category != FAVR_CAT_NAME:
		return

	user = users.User.get_user( event.rating.userid )
	if not user:
		return
	if bool(event.rating):
		# ok, add it to the shared objects so that it can be seen
		user._addSharedObject( modified_object )
	else:
		user._removeSharedObject( modified_object )

del _view_defaults
del _c_view_defaults
del _r_view_defaults
del _d_view_defaults
