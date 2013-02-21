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

from nti.externalization.oids import toExternalOID

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

	def createContentObject( self, user, datatype, externalValue, creator ):
		return obj_io.create_modeled_content_object( self.dataserver, user, datatype, externalValue, creator )

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
		datatype = None
		# TODO: Which should have priority, class in the data,
		# or mime-type in the headers (or data?)?
		if 'Class' in externalValue and externalValue['Class']:
			# Convert unicode to ascii
			datatype = str( externalValue['Class'] ) + 's'
		else:
			datatype = obj_io.class_name_from_content_type( self.request )
			datatype = datatype + 's' if datatype else None

		containedObject = self.createContentObject( owner, datatype, externalValue, creator )
		if containedObject is None or not frm_interfaces.IPost.providedBy( containedObject ):
			transaction.doom()
			logger.debug( "Failing to POST: input of unsupported/missing Class: %s %s", datatype, externalValue )
			raise hexc.HTTPUnprocessableEntity( 'Unsupported/missing Class' )


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
		topic.title = topic.story.title


		name = INameChooser( context ).chooseName( topic.title, topic )

		lifecycleevent.created( topic )
		lifecycleevent.created( containedObject )


		context[name] = topic # Now store the topic and fire added
		topic.id = name # match these things
		containedObject.containerId = topic.id

		lifecycleevent.added( containedObject )

		# Respond with the generic location of the object, within
		# the owner's Objects tree.
		self.request.response.location = self.request.resource_url( owner,
																	'Objects',
																	toExternalOID( topic ) )


		return topic

from .dataserver_pyramid_views import _GenericGetView as GenericGetView
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=frm_interfaces.IPersonalBlog,
			  request_method='GET' )
class BlogGetView(GenericGetView):
			pass
