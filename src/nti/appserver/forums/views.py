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
from nti.contentsearch import interfaces as search_interfaces

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

		added_headline = False
		if interface.providedBy( topic ).get('headline'):
			# not all containers have headlines; those that don't simply use
			# the incoming post as a template
			topic_post.__parent__ = topic # must set __parent__ first for acquisition to work
			added_headline = True
			topic.headline = topic_post
		# Business rule: titles of the personal blog entry match the post
		topic.title = topic_post.title
		topic.description = external_value.get( 'description', topic.title )

		# For these, the name matters. We want it to be as pretty as we can get
		# TODO: We probably need to register an IReservedNames that forbids
		# _VIEW_CONTENTS and maybe some other stuff
		name = INameChooser( forum ).chooseName( topic.title, topic )

		lifecycleevent.created( topic )
		if added_headline:
			lifecycleevent.created( topic_post )


		forum[name] = topic # Now store the topic and fire lifecycleevent.added
		topic.id = name # match these things. ID is local within container
		topic.containerId = forum.NTIID

		if added_headline:
			topic_post.containerId = topic.NTIID
			# The headline should be a sub-location of the topic, so when
			# the added event was fired for the topic, it was dispatchToSublocations sent
			# along. This also ensures the headline gets its intid. So we don't need to
			# manually send an added event.

		# Respond with the pretty location of the object, within the blog
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_path( topic )

		return topic

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_CREATE,
			  context=frm_interfaces.IPersonalBlog,
			  request_method='POST' )
class PersonalBlogPostView(_AbstractForumPostView):
	""" Given an incoming IPost, creates a new topic in the blog """

	_constraint = frm_interfaces.IPersonalBlogEntryPost.providedBy
	_override_content_type = PersonalBlogEntryPost.mimeType
	_factory = PersonalBlogEntry

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_CREATE,
			  context=frm_interfaces.ICommunityBoard,
			  request_method='POST' )
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

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_CREATE,
			  context=frm_interfaces.ICommunityForum,
			  request_method='POST' )
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

		incoming_post.id = name # match these things before we fire events
		incoming_post.containerId = topic.NTIID

		topic[name] = incoming_post # Now store the topic and fire added

		# Respond with the pretty location of the object
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_path( incoming_post )

		return incoming_post

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_CREATE,
			  context=frm_interfaces.ICommunityHeadlineTopic,
			  request_method='POST' )
class CommunityHeadlineTopicPostView(_AbstractTopicPostView):

	_constraint = frm_interfaces.IGeneralForumComment.providedBy
	_override_content_type = GeneralForumComment.mimeType

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_CREATE,
			  context=frm_interfaces.IPersonalBlogEntry,
			  request_method='POST' )
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
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_READ,
				request_method='GET' )
class ForumGetView(GenericGetView):
	""" Support for simply returning the blog item """


@view_config( context=frm_interfaces.IBoard )
@view_config( context=frm_interfaces.IForum )
@view_config( context=frm_interfaces.IHeadlineTopic )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_READ,
				name=VIEW_CONTENTS,
				request_method='GET')
class ForumContentsGetView(UGDQueryView):
	""" The /contents view for the forum objects we are using.

	The contents fully support the same sorting and paging parameters as
	the UGD views. """

	def __init__( self, request ):
		self.request = request
		super(ForumContentsGetView,self).__init__( request, the_user=self, the_ntiid=self.request.context.__name__ )

		# The user/community is really the 'owner' of the data
		self.user = find_interface(  self.request.context, nti_interfaces.IEntity )

	def getObjectsForId( self, *args ):
		return (self.request.context,)

@view_config( context=frm_interfaces.ICommunityBoard )
class CommunityBoardContentsGetView(ForumContentsGetView):

	def __init__( self, request ):
		# Make sure that if it's going to have a default, it does
		frm_interfaces.ICommunityForum( request.context.creator, None )
		super(CommunityBoardContentsGetView,self).__init__( request )



@view_config( context=frm_interfaces.IHeadlineTopic,
			  name='feed.atom' )
@view_config( context=frm_interfaces.IHeadlineTopic,
			  name='feed.rss' )
@view_config( context=frm_interfaces.IForum,
			  name='feed.atom' )
@view_config( context=frm_interfaces.IForum,
			  name='feed.rss' )
@view_defaults( route_name='objects.generic.traversal',
				permission=nauth.ACT_READ,
				request_method='GET',
				http_cache=datetime.timedelta(hours=1))
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
@view_config( context=frm_interfaces.IPersonalBlogEntryPost )
@view_config( context=frm_interfaces.IPersonalBlogComment )
@view_config( context=frm_interfaces.IGeneralForumComment )
@view_config( context=frm_interfaces.ICommunityHeadlinePost )
@view_config( context=frm_interfaces.ICommunityForum )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='PUT' )
class ForumObjectPutView(UGDPutView):
	""" Editing an existing forum post, etc """
	# Exists entirely for registration sake.

@view_config( context=frm_interfaces.ICommunityHeadlineTopic )
@view_config( context=frm_interfaces.IPersonalBlogEntry )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_DELETE,
				request_method='DELETE' )
class HeadlineTopicDeleteView(UGDDeleteView):
	""" Deleting an existing topic """

	## Deleting an IPersonalBlogEntry winds up in users.users.py:user_willRemoveIntIdForContainedObject,
	## thus posting the usual activitystream DELETE notifications

	def _do_delete_object( self, theObject ):
		# Delete from enclosing container
		del aq_base(theObject.__parent__)[theObject.__name__]
		return theObject

@view_config( context=frm_interfaces.ICommunityForum )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_DELETE,
				request_method='DELETE' )
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
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_DELETE,
				request_method='DELETE' )
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
		raise NotImplementedError() # pragma: no cover
	@abstractmethod
	def _test_provides(self, topic):
		raise NotImplementedError() # pragma: no cover

	def _did_modify_topic( self, blog_entry, oldSharingTargets ):
		"Fire off a modified event when the publication status changes. The event notes the sharing has changed."
		provides = interface.providedBy( blog_entry )
		attributes = []
		for attr_name in 'sharedWith', 'sharingTargets':
			attr = provides.get( attr_name )
			if attr:
				iface_providing = attr.interface
				attributes.append( lifecycleevent.Attributes( iface_providing, attr_name ) )

		event = ObjectSharingModifiedEvent( blog_entry, *attributes, oldSharingTargets=oldSharingTargets )
		notify( event )
		return event

	def __call__(self):
		request = self.request
		topic = request.context
		if self._test_provides( topic ):
			oldSharingTargets = set(topic.sharingTargets)

			self._do_provide( topic )

			# Ordinarily, we don't need to dispatch to sublocations a change
			# in the parent (hence why it is not a registered listener).
			# But here we know that the sharing is propagated automatically
			# down, so we do.
			event = self._did_modify_topic( topic, oldSharingTargets )
			dispatchToSublocations( topic, event )

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
		interface.alsoProvides( topic, self._iface )
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
		interface.noLongerProvides( topic, self._iface )
	def _test_provides( self, topic ):
		return nti_interfaces.IDefaultPublished.providedBy( topic )


### Events
## TODO: Under heavy construction
###
from nti.dataserver import activitystream_change

def _stream_event_for_comment( comment, change_type=nti_interfaces.SC_CREATED ):
	# Now, construct the (artificial) change notification.
	change = activitystream_change.Change(change_type, comment)
	change.creator = comment.creator
	change.object_is_shareable = False

	return change


@component.adapter( frm_interfaces.IPersonalBlogComment, lifecycleevent.IObjectAddedEvent )
def notify_online_author_of_comment( comment, event ):
	"""
	When a comment is added to a blog post, notify the blog's
	author.
	"""

	# First, find the author of the blog entry. It will be the parent, the only
	# user in the lineage
	blog_author = find_interface( comment, nti_interfaces.IUser )

	# Now, construct the (artificial) change notification.
	change = _stream_event_for_comment( comment )

	# Store it in the author persistently. Notice that this is a private
	# API, subject to change.
	# This also has the effect of sending a socket notification, if needed.
	# Because it is not shared directly with the author, it doesn't go
	# in the shared data
	assert not comment.isSharedDirectlyWith( blog_author )


	if blog_author != comment.creator:
		blog_author._noticeChange( change, force=True )

	# (Except for being in the stream, the effect of the notification can be done with component.handle( blog_author, change ) )

	# Also do the same for of the dynamic types it is shared with,
	# thus sharing the same change object
	#_send_stream_event_to_targets( change, comment.sharingTargets )

###
## NOTE: You cannot send a stream change on an object deleted event.
## See HeadlineTopicDeleteView and the place it points to. This is already
## handled.

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
