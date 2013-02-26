#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and other functions related to forums and blogs.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from ZODB.interfaces import IConnection

from nti.appserver.traversal import find_interface
from nti.appserver._util import uncached_in_response
from nti.appserver import interfaces as app_interfaces
from nti.appserver._view_utils import AbstractAuthenticatedView
from nti.appserver._view_utils import ModeledContentUploadRequestUtilsMixin

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces
from nti.dataserver.contenttypes.forums.forum import PersonalBlog
from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry
from nti.dataserver.contenttypes.forums.post import PersonalBlogEntryPost
from nti.dataserver.contenttypes.forums.post import PersonalBlogComment
from nti.dataserver.contenttypes.forums.post import Post

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import StandardExternalFields

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope.container.interfaces import INameChooser
from zope import component
from zope import interface
from zope import lifecycleevent
from zope import schema
from zope.schema import interfaces as sch_interfaces

import pyramid.httpexceptions  as hexc
import transaction
import zope.annotation.factory

@interface.implementer(frm_interfaces.IPersonalBlog)
@component.adapter(nti_interfaces.IUser)
def _DefaultUserForumFactory(  ):
	forum = PersonalBlog()
	return forum

@interface.implementer(frm_interfaces.IPersonalBlog)
@component.adapter(nti_interfaces.IUser)
def DefaultUserForumFactory(user):
	# The right key is critical. 'Blog' is the pretty external name (see dataserver_pyramid_traversal)
	forum = zope.annotation.factory(_DefaultUserForumFactory, key='Blog')(user)
	if not forum._p_mtime:
		jar = IConnection( user, None )
		if jar:
			jar.add( forum ) # ensure we store with the user
		forum.title = user.username
		forum.creator = user
		errors = schema.getValidationErrors( frm_interfaces.IPersonalBlog, forum )
		if errors:
			__traceback_info__ = errors
			raise errors[0][1]
	return forum

class _AbstractIPostPOSTView(AbstractAuthenticatedView,ModeledContentUploadRequestUtilsMixin):
	""" HTTP says POST creates a NEW entity under the Request-URI """
	# Therefore our context is a container, and we should respond created.

	_constraint = frm_interfaces.IPost.providedBy

	_override_content_type = None
	_allowed_content_types = ()

	def _transformContentType( self, contenttype ):
		if self._override_content_type and contenttype in self._allowed_content_types:
			contenttype = self._override_content_type
		return contenttype

	def _read_incoming_post( self ):
		# TODO: Ripped from ugd_edit_views
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

		return containedObject


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_CREATE,
			  context=frm_interfaces.IPersonalBlog,
			  request_method='POST' )
class PersonalBlogEntryPostView(_AbstractIPostPOSTView):
	""" HTTP says POST creates a NEW entity under the Request-URI """
	# Therefore our context is a container, and we should respond created.

	_constraint = frm_interfaces.IPersonalBlogEntryPost.providedBy

	_override_content_type = PersonalBlogEntryPost.mimeType

	_allowed_content_types = ('Post', Post.mimeType, 'Posts' )

	def _do_call( self ):
		blog = self.request.context
		containedObject = self._read_incoming_post()

		# Now the topic
		topic = PersonalBlogEntry()
		topic.creator = self.getRemoteUser()
		containedObject.__parent__ = topic # must set __parent__ first for acquisition to work

		topic.headline = containedObject
		# Business rule: titles of the personal blog entry match the post
		topic.title = topic.headline.title
		topic.description = topic.title

		# For these, the name matters. We want it to be as pretty as we can get
		# TODO: We probably need to register an IReservedNames that forbids
		# _VIEW_CONTENTS and maybe some other stuff
		name = INameChooser( blog ).chooseName( topic.title, topic )

		lifecycleevent.created( topic )
		lifecycleevent.created( containedObject )


		blog[name] = topic # Now store the topic and fire added
		topic.id = name # match these things
		containedObject.containerId = topic.id # TODO:  This is not right, containerId is meant to be global

		lifecycleevent.added( containedObject )

		# Respond with the generic location of the object, within
		# the owner's Objects tree.
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_url( self.getRemoteUser(),
																	'Objects',
																	to_external_ntiid_oid( topic ) )

		return topic

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_CREATE,
			  # NOTE that everywhere we use IHeadlineTopic with different verbs, we must stay at that level.
			  # we cannot mix this with IPersonalBlogEntry
			  context=frm_interfaces.IHeadlineTopic,
			  request_method='POST' )
class TopicPostView(_AbstractIPostPOSTView):

	_constraint = frm_interfaces.IPersonalBlogComment.providedBy

	_override_content_type = PersonalBlogComment.mimeType
	_allowed_content_types = ('Post', Post.mimeType, 'Posts')

	def _do_call( self ):
		incoming_post = self._read_incoming_post()

		topic = self.request.context

		# The actual name of these isn't tremendously important
		name = topic.generateId( prefix='post' )

		lifecycleevent.created( incoming_post )

		topic[name] = incoming_post # Now store the topic and fire added
		incoming_post.id = name # match these things
		incoming_post.containerId = topic.id # TODO:  This is not right, containerId is meant to be global

		# Respond with the generic location of the object, within
		# the owner's Objects tree.
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_url( self.getRemoteUser(),
																	'Objects',
																	to_external_ntiid_oid( incoming_post ) )

		return incoming_post

from .dataserver_pyramid_views import _GenericGetView as GenericGetView
from .ugd_edit_views import UGDPutView
from .ugd_edit_views import UGDDeleteView
from .ugd_query_views import _UGDView as UGDQueryView

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=frm_interfaces.IPersonalBlog,
			  request_method='GET' )
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=frm_interfaces.IHeadlineTopic,
			  request_method='GET' )
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=frm_interfaces.IPost,
			  request_method='GET' )
class ForumGetView(GenericGetView):
	""" Support for simply returning the blog item """

_VIEW_CONTENTS = 'contents'
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=frm_interfaces.IPersonalBlog,
			  name=_VIEW_CONTENTS,
			  request_method='GET' )
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=frm_interfaces.IHeadlineTopic,
			  name=_VIEW_CONTENTS,
			  request_method='GET' )
class ForumContentsGetView(UGDQueryView):
	""" The /contents view for the forum objects we are using.

	The contents fully support the same sorting and paging parameters as
	the UGD views. """

	def __init__( self, request ):
		self.request = request
		super(ForumContentsGetView,self).__init__( request, the_user=self, the_ntiid=self.request.context.__name__ )

		# The user is really the 'owner' of the data
		self.user = find_interface(  self.request.context, nti_interfaces.IUser )

	def getObjectsForId( self, *args ):
		return (self.request.context,)

import datetime
from .ugd_feed_views import AbstractFeedView
@view_config( context=frm_interfaces.IHeadlineTopic,
			  name='feed.atom' )
@view_config( context=frm_interfaces.IHeadlineTopic,
			  name='feed.rss' )
@view_config( context=frm_interfaces.IPersonalBlog,
			  name='feed.atom' )
@view_config( context=frm_interfaces.IPersonalBlog,
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


@interface.implementer(app_interfaces.IUserCheckout)
class ForumCheckoutAdapter(object):

	def __init__( self, context, request ):
		self.context = context
		self.request = request

	def checkObjectOutFromUserForUpdate( self, *args ):
		"""
		Users do not contain these post objects, they live outside that hierarchy
		(This might need to change.) As a consequence, there is no checking out that happens.
		"""
		return self.context

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_UPDATE,
			  context=frm_interfaces.IPost,
			  request_method='PUT' )
class PostPutView(UGDPutView):
	""" Editing an existing forum post """
	# Exists entirely for registration sake

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_DELETE,
			  context=frm_interfaces.IPost,
			  request_method='DELETE' )
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_DELETE,
			  context=frm_interfaces.IHeadlineTopic,
			  request_method='DELETE' )
class PostOrForumDeleteView(UGDDeleteView):
	""" Deleting an existing forum/post """

	def _do_delete_object( self, theObject ):
		# Delete from enclosing container
		del aq_base(theObject.__parent__)[theObject.__name__]
		return theObject

from Acquisition import aq_base
@component.adapter(frm_interfaces.IPost, lifecycleevent.IObjectModifiedEvent)
def match_title_of_post_to_blog( post, event ):
	"When the main story of a story topic (blog post) is modified, match the titles"

	if frm_interfaces.IHeadlineTopic.providedBy( post.__parent__ ) and aq_base(post) is aq_base(post.__parent__.headline) and post.title != post.__parent__.title:
		post.__parent__.title = post.title
	return

# Notice we do not declare what we adapt--we adapt too many things
# that share no common ancestor. (We could be declared on IContainer,
# but its not clear what if any IContainers we externalize besides
# the forum objects)
from nti.dataserver import links
from zope.container.interfaces import ILocation
from ._util import AbstractTwoStateViewLinkDecorator
from ._view_utils import get_remote_user
from pyramid.threadlocal import get_current_request
@interface.implementer( ext_interfaces.IExternalMappingDecorator )
class ForumObjectContentsLinkProvider(object):
	"""
	Decorate forum object externalizations with a link pointing to their
	children (the contents).
	"""

	def __init__( self, context ):
		pass

	def decorateExternalMapping( self, context, mapping ):
		# We only do this for parented objects. Otherwise, we won't
		# be able to render the links. A non-parented object is usually
		# a weakref to an object that has been left around
		# in somebody's stream.
		# All forum objects should have fully traversable paths by themself,
		# without considering acquired info (NTIIDs from the User would mess
		# up rendering)
		context = aq_base( context )
		if not context.__parent__:
			return


		# /path/to/forum/topic/contents --> note that contents is not an @@ view,
		# simply named. This is prettier, but if we need to we can easily @@ it
		link = links.Link( context, rel=_VIEW_CONTENTS, elements=(_VIEW_CONTENTS,) )
		interface.alsoProvides( link, ILocation )
		link.__name__ = ''
		link.__parent__ = context

		_links = mapping.setdefault( StandardExternalFields.LINKS, [] )
		_links.append( link )

### Publishing workflow

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(frm_interfaces.IPersonalBlogEntry)
class PublishLinkDecorator(AbstractTwoStateViewLinkDecorator):
	"""
	Adds the appropriate publish or unpublish link
	"""
	false_view = 'publish'
	true_view = 'unpublish'

	def predicate( self, context, current_username ):
		if nti_interfaces.IDefaultPublished.providedBy( context ):
			return True

	def decorateExternalMapping( self, context, mapping ):
		# Only for the owner
		current_user = get_remote_user( get_current_request() )
		if not current_user or current_user != context.creator:
			return
		super(PublishLinkDecorator,self).decorateExternalMapping( context, mapping )

from nti.dataserver.authorization_acl import AbstractCreatedAndSharedACLProvider
from nti.dataserver.authentication import _dynamic_memberships_that_participate_in_security
@component.adapter(frm_interfaces.IPersonalBlogEntry)
class _PersonalBlogEntryACLProvider(AbstractCreatedAndSharedACLProvider):

	_DENY_ALL = True
	_REQUIRE_CREATOR = True

	# People it is shared with can create within it
	# as well as see it
	_PERMS_FOR_SHARING_TARGETS = (nauth.ACT_READ,nauth.ACT_CREATE)
	def _get_sharing_target_names( self ):
		if nti_interfaces.IDefaultPublished.providedBy( self.context ):
			# TODO: Using a private function
			return _dynamic_memberships_that_participate_in_security( find_interface( self.context, nti_interfaces.IUser ) )

		return ()

@component.adapter(frm_interfaces.IPersonalBlog)
class _PersonalBlogACLProvider(AbstractCreatedAndSharedACLProvider):

	_DENY_ALL = False

	# We want posts to get their own acl, giving the creator full
	# control. We also want the owner of the topic they are in to get
	# control too. Hence we subclass this one (rather than ShareableModContentACLProvider)
	# and turn inheritance on

	def _get_sharing_target_names( self ):
		return ()

@component.adapter(frm_interfaces.IPost)
class _PostACLProvider(AbstractCreatedAndSharedACLProvider):

	_DENY_ALL = False

	# We want posts to get their own acl, giving the creator full
	# control. We also want the owner of the topic they are in to get
	# control too. Hence we subclass this one (rather than ShareableModContentACLProvider)
	# and turn inheritance on

	def _get_sharing_target_names( self ):
		return ()

from ._adapters import GenericModeledContentExternalFieldTraverser
@component.adapter(frm_interfaces.IPost)
class _PostFieldTraverser(GenericModeledContentExternalFieldTraverser):
	"Disallow updates to the sharedWith field of blog posts/comments"
	_allowed_fields = tuple( set(GenericModeledContentExternalFieldTraverser._allowed_fields) - set( ('sharedWith',)) )



@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=frm_interfaces.IPersonalBlogEntry,
			  permission=nauth.ACT_UPDATE,
			  request_method='POST',
			  name='publish')
def _PublishView(request):
	interface.alsoProvides( request.context, nti_interfaces.IDefaultPublished )
	return uncached_in_response( request.context )


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=frm_interfaces.IPersonalBlogEntry,
			  permission=nauth.ACT_UPDATE,
			  request_method='POST',
			  name='unpublish')
def _UnpublishView(request):
	interface.noLongerProvides( request.context, nti_interfaces.IDefaultPublished )
	return uncached_in_response( request.context )
