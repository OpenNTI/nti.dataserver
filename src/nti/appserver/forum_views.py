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

from nti.appserver import _external_object_io as obj_io
from nti.appserver._view_utils import AbstractAuthenticatedView
from nti.appserver._view_utils import ModeledContentUploadRequestUtilsMixin

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces
from nti.dataserver.contenttypes.forums.forum import PersonalBlog
from nti.dataserver.contenttypes.forums.topic import StoryTopic

from nti.externalization.oids import to_external_ntiid_oid

from pyramid.view import view_config
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
	forum = zope.annotation.factory(_DefaultUserForumFactory)(user)
	if not forum._p_mtime:
		jar = IConnection( user, None )
		if jar:
			jar.add( forum ) # ensure we store with the user
		forum.title = user.username
		forum.__name__ = unicode(forum.__name__, 'ascii')
		errors = schema.getValidationErrors( frm_interfaces.IPersonalBlog, forum )
		if errors:
			__traceback_info__ = errors
			raise errors[0][1]
	return forum

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_CREATE,
			  context=frm_interfaces.IPersonalBlog,
			  request_method='POST' )
class ForumPostView(AbstractAuthenticatedView,ModeledContentUploadRequestUtilsMixin):
	""" HTTP says POST creates a NEW entity under the Request-URI """
	# Therefore our context is a container, and we should respond created.

	def __call__( self ):
		try:
			return self._do_call()
		except sch_interfaces.ValidationError as e:
			obj_io.handle_validation_error( self.request, e )

	def _do_call( self ):
		owner = creator = self.getRemoteUser()
		context = self.request.context
		externalValue = self.readInput()

		# TODO: Ripped from ugd_edit_views
		datatype = self.findContentType( externalValue )

		containedObject = self.createAndCheckContentObject( owner, datatype, externalValue, creator, frm_interfaces.IPost.providedBy )
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


		# Now the topic
		topic = StoryTopic()
		containedObject.__parent__ = topic

		topic.story = containedObject
		# Business rule: titles of the personal blog entry match the post
		topic.title = topic.story.title
		topic.description = topic.title


		name = INameChooser( context ).chooseName( topic.title, topic )

		lifecycleevent.created( topic )
		lifecycleevent.created( containedObject )


		context[name] = topic # Now store the topic and fire added
		topic.id = name # match these things
		containedObject.containerId = topic.id # TODO:  This is not right, containerId is meant to be global

		lifecycleevent.added( containedObject )

		# Respond with the generic location of the object, within
		# the owner's Objects tree.
		self.request.response.status_int = 201 # created
		self.request.response.location = self.request.resource_url( owner,
																	'Objects',
																	to_external_ntiid_oid( topic ) )


		return topic

from .dataserver_pyramid_views import _GenericGetView as GenericGetView
from .ugd_edit_views import UGDPutView
from .ugd_edit_views import UGDDeleteView

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=frm_interfaces.IPersonalBlog,
			  request_method='GET' )
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=frm_interfaces.IStoryTopic,
			  request_method='GET' )
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=frm_interfaces.IPost,
			  request_method='GET' )
class BlogGetView(GenericGetView):
	""" Support for simply returning the blog item """

class _CheckObjectOutMixin(object):
	def checkObjectOutFromUserForUpdate( self, *args ):
		"""
		Users do not contain these post objects, they live outside that hierarchy
		(This might need to change.) As a consequence, there is no checking out that happens.
		"""
		return self.request.context


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_UPDATE,
			  context=frm_interfaces.IPost,
			  request_method='PUT' )
class PostPutView(_CheckObjectOutMixin, UGDPutView):
	""" Editing an existing forum post """

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_DELETE,
			  context=frm_interfaces.IPost,
			  request_method='DELETE' )
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_DELETE,
			  context=frm_interfaces.IStoryTopic,
			  request_method='DELETE' )
class PostOrForumDeleteView(_CheckObjectOutMixin, UGDDeleteView):
	""" Deleting an existing forum/post """

	def _do_delete_object( self, theObject ):
		# Delete from enclosing container
		del aq_base(theObject.__parent__)[theObject.__name__]
		return theObject

from Acquisition import aq_base
@component.adapter(frm_interfaces.IPost, lifecycleevent.IObjectModifiedEvent)
def match_title_of_post_to_blog( post, event ):
	"When the main story of a story topic (blog post) is modified, match the titles"

	if frm_interfaces.IStoryTopic.providedBy( post.__parent__ ) and aq_base(post) is aq_base(post.__parent__.story) and post.title != post.__parent__.title:
		post.__parent__.title = post.title
