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
from nti.chatserver import interfaces as chat_interfaces
from nti.contentsearch import interfaces as search_interfaces


# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

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

@interface.implementer(frm_interfaces.IPersonalBlog)
@component.adapter(nti_interfaces.IUser)
def DefaultUserForumFactory(user):
	# The right key is critical. 'Blog' is the pretty external name (see dataserver_pyramid_traversal)

	containers = getattr( user, 'containers', None ) # some types of users (test users usually) have no containers
	if containers is None:
		return None

	# For convenience, we register the container with
	# both its NTIID and its short name
	forum = containers.getContainer( _UserBlogCollection.name )
	if forum is None:
		forum = PersonalBlog()
		forum.__parent__ = user
		forum.creator = user
		forum.__name__ = _UserBlogCollection.name
		forum.title = user.username
		# TODO: Events?
		containers.addContainer( _UserBlogCollection.name, forum, locate=False )
		containers.addContainer( forum.NTIID, forum, locate=False )

		jar = IConnection( user, None )
		if jar:
			jar.add( forum ) # ensure we store with the user
		errors = schema.getValidationErrors( frm_interfaces.IPersonalBlog, forum )
		if errors:
			__traceback_info__ = errors
			raise errors[0][1]
	return forum


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
		entry_post = self._read_incoming_post()

		# Now the topic
		entry = PersonalBlogEntry()
		entry.creator = self.getRemoteUser()
		entry_post.__parent__ = entry # must set __parent__ first for acquisition to work

		entry.headline = entry_post
		# Business rule: titles of the personal blog entry match the post
		entry.title = entry.headline.title
		entry.description = entry.title

		# For these, the name matters. We want it to be as pretty as we can get
		# TODO: We probably need to register an IReservedNames that forbids
		# _VIEW_CONTENTS and maybe some other stuff
		name = INameChooser( blog ).chooseName( entry.title, entry )

		lifecycleevent.created( entry )
		lifecycleevent.created( entry_post )


		blog[name] = entry # Now store the topic and fire added
		entry.id = name # match these things. ID is local within container
		entry.containerId = blog.NTIID
		entry_post.containerId = entry.NTIID

		lifecycleevent.added( entry_post )

		# Respond with the generic location of the object, within
		# the owner's Objects tree.
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_url( self.getRemoteUser(),
																	'Objects',
																	to_external_ntiid_oid( entry ) )
		return entry

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
		incoming_post.containerId = topic.NTIID

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

@view_config( context=frm_interfaces.IHeadlineTopic )
@view_config( context=frm_interfaces.IPersonalBlog )
@view_config( context=frm_interfaces.IPersonalBlogComment )
@view_config( context=frm_interfaces.IPersonalBlogEntryPost )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_READ,
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

@view_config( context=frm_interfaces.IHeadlinePost )
@view_config( context=frm_interfaces.IPersonalBlogEntryPost )
@view_config( context=frm_interfaces.IPersonalBlogComment )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='PUT' )
class PostPutView(UGDPutView):
	""" Editing an existing forum post """
	# Exists entirely for registration sake


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_DELETE,
			  context=frm_interfaces.IHeadlineTopic,
			  request_method='DELETE' )
class HeadlineTopicDeleteView(UGDDeleteView):
	""" Deleting an existing forum """

	## Deleting winds up in users.users.py:user_willRemoveInteIdForContainedObject,
	## thus posting the usual activitystream DELETE notifications

	def _do_delete_object( self, theObject ):
		# Delete from enclosing container
		del aq_base(theObject.__parent__)[theObject.__name__]
		return theObject


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_DELETE,
			  context=frm_interfaces.IPersonalBlogComment,
			  request_method='DELETE' )
class PostDeleteView(UGDDeleteView):
	""" Deleting an existing blog comment.

	This is somewhat unusual as we leave an object behind to mark
	the object as deleted (in fact, we leave the original object
	behind to preserve its timestamps and IDs) we only apply a marker and
	clear the body.
	"""

	def _do_delete_object( self, theObject ):
		deleting = aq_base(theObject)
		interface.alsoProvides( deleting, app_interfaces.IDeletedObjectPlaceholder )

		# TODO: Events need to fire to unindex, once we figure
		# out what those are
		# We are I18N as externalization time
		deleting.title = None
		deleting.body = None
		deleting.tags = ()
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

		# TODO: This can be generalized by using the component
		# registry in the same way Pyramid itself does. With a lookup like
		#   adapters.lookupAll( (IViewClassifier, request.request_iface, context_iface), IView )
		# you get back a list of (name, view) pairs that are applicable.
		# ISecuredViews (which include IMultiViews) have a __permitted__ that checks ACLs;
		# if it doesn't pass then that one is obviously filtered out. IMultiViews have a
		# match and __permitted__ method, __permitted__ using match(). The main
		# trouble is filtering out the general views (i.e., those that don't specify an interface)
		# that we don't want to return for everything

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
@component.adapter(frm_interfaces.IPersonalBlogEntry)
class _PersonalBlogEntryACLProvider(AbstractCreatedAndSharedACLProvider):

	_DENY_ALL = True
	_REQUIRE_CREATOR = True

	# People it is shared with can create within it
	# as well as see it
	_PERMS_FOR_SHARING_TARGETS = (nauth.ACT_READ,nauth.ACT_CREATE)
	def _get_sharing_target_names( self ):
		# The PersonalBlogEntry takes care of the right sharing settings itself,
		# based on the publication status
		return self.context.sharingTargets


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
	# TODO: Hooked directly up to temp_dispatch_to_indexer
	temp_dispatch_to_indexer( request.context.headline, None )
	return uncached_in_response( request.context )


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=frm_interfaces.IPersonalBlogEntry,
			  permission=nauth.ACT_UPDATE,
			  request_method='POST',
			  name='unpublish')
def _UnpublishView(request):
	interface.noLongerProvides( request.context, nti_interfaces.IDefaultPublished )
	# TODO: While we have temp_dispatch_to_indexer in place, when we unpublish
	# do we need to unindex the comments too?
	return uncached_in_response( request.context )

### Events
## TODO: Under heavy construction
###
from nti.dataserver import activitystream_change
from zope.event import notify

def _stream_event_for_comment( comment ):
	# Now, construct the (artificial) change notification. Notice this is never
	# persisted anywhere
	change = activitystream_change.Change( nti_interfaces.SC_CREATED, comment )
	change.creator = comment.creator

	return change

@component.adapter( frm_interfaces.IPersonalBlogComment, lifecycleevent.IObjectAddedEvent )
def notify_online_author_of_comment( comment, event ):
	"""
	When a comment is added to a blog post, notify the blog's
	author.
	"""

	# First, find the author of the blog entry. It will be the parent, the only
	# user in the lineage
	author = find_interface( comment, nti_interfaces.IUser )

	# Now, construct the (artificial) change notification. Notice this is never
	# persisted anywhere
	change = _stream_event_for_comment( comment )

	notify( chat_interfaces.DataChangedUserNotificationEvent( (author.username,), change ) )


@component.adapter( frm_interfaces.IPersonalBlogComment, lifecycleevent.IObjectAddedEvent )
def temp_dispatch_to_indexer( comment, event ):
	# Direct dispatch comment posted events for indexing when created

	indexmanager = component.queryUtility( search_interfaces.IIndexManager )
	dataserver = component.queryUtility( nti_interfaces.IDataserver )

	if indexmanager and dataserver:

		change = _stream_event_for_comment( comment )
		# Now index the comment for the creator and all the sharing targets. This is just
		# like what the User object itself does (except we don't need to expand DFL/communities)

		indexmanager.onChange( dataserver, change, comment.creator, broadcast=True ) # The creator gets it as a broadcast
		for target in comment.sharingTargets:
			indexmanager.onChange( dataserver, change, target )
