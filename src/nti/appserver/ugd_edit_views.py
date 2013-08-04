#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User-generated data CRUD functions.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import transaction

from zope import interface
from zope import lifecycleevent
from zope.container.interfaces import InvalidContainerType

from pyramid import traversal

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardInternalFields
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.oids import to_external_ntiid_oid as toExternalOID

from nti.appserver import httpexceptions as hexc
from nti.appserver import interfaces as app_interfaces
from nti.appserver._view_utils import AbstractAuthenticatedView
from nti.appserver._view_utils import ModeledContentEditRequestUtilsMixin
from nti.appserver._view_utils import ModeledContentUploadRequestUtilsMixin

from nti.assessment import interfaces as asm_interfaces

def _id(x): return x

#@component.adapter
@interface.implementer(app_interfaces.INewObjectTransformer)
def _question_submission_transformer( obj ):
	# Grade it, by adapting the object into an IAssessedQuestion
	return asm_interfaces.IQAssessedQuestion

#@component.adapter
@interface.implementer(app_interfaces.INewObjectTransformer)
def _question_set_submission_transformer( obj ):
	# Grade it, by adapting the object into an IAssessedQuestionSet
	return asm_interfaces.IQAssessedQuestionSet


class UGDPostView(AbstractAuthenticatedView,ModeledContentUploadRequestUtilsMixin):
	""" HTTP says POST creates a NEW entity under the Request-URI """
	# Therefore our context is a container, and we should respond created.

	def _do_call( self ):
		creator = self.getRemoteUser()
		context = self.request.context
		# If our context contains a user resource, then that's where we should be trying to
		# create things
		owner_root = traversal.find_interface( context, nti_interfaces.IUser )
		if owner_root is not None:
			owner_root = getattr( owner_root, 'user', owner_root ) # migration compat
		if owner_root is None:
			owner_root = traversal.find_interface( context, nti_interfaces.IUser )
		if owner_root is None and hasattr( context, 'container' ):
			owner_root = traversal.find_interface( context.container, nti_interfaces.IUser )

		owner = owner_root if owner_root else creator
		externalValue = self.readInput()
		datatype = self.findContentType( externalValue )

		containedObject = self.createAndCheckContentObject( owner, datatype, externalValue, creator )

		containedObject.creator = creator

		# The process of updating may need to index and create KeyReferences
		# so we need to have a jar. We don't have a parent to inherit from just yet
		# (If we try to set the wrong one, it messes with some events and some
		# KeyError detection in the containers)
		#containedObject.__parent__ = owner
		owner_jar = getattr( owner, '_p_jar', None )
		if owner_jar and getattr( containedObject, '_p_jar', self) is None:
			owner_jar.add( containedObject )

		# Update the object, but don't fire any modified events. We don't know
		# if we'll keep this object yet, and we haven't fired a created event
		self.updateContentObject( containedObject, externalValue, set_id=True, notify=False )
		try:
			transformedObject = self.request.registry.queryAdapter( containedObject,
																	app_interfaces.INewObjectTransformer,
																	default=_id )( containedObject )
		except (TypeError,ValueError,AssertionError,KeyError) as e:
			transaction.doom()
			logger.warn( "Failed to transform incoming object", exc_info=True)
			raise hexc.HTTPUnprocessableEntity( e.message )
		# If we transformed, copy the container and creator
		if transformedObject is not containedObject:
			transformedObject.creator = creator
			if 	getattr(containedObject, StandardInternalFields.CONTAINER_ID, None) \
				and not getattr(transformedObject, StandardInternalFields.CONTAINER_ID, None):
				transformedObject.containerId = containedObject.containerId
				# TODO: JAM: I really don't like doing this. Straighten out the
				# location of IContained so that things like assessment can implement it
				if not nti_interfaces.IContained.providedBy(transformedObject):
					interface.alsoProvides(transformedObject, nti_interfaces.IContained)
			containedObject = transformedObject
		# TODO: The WSGI code would attempt to infer a containerID from the
		# path. Should we?
		if not getattr( containedObject, StandardInternalFields.CONTAINER_ID, None ):
			transaction.doom()
			logger.debug( "Failing to POST: input of unsupported/missing ContainerId" )
			e = InvalidContainerType( "Unsupported/missing ContainerId", StandardExternalFields.CONTAINER_ID, None )
			e.field = nti_interfaces.IContained['containerId']
			raise e

		if hasattr( containedObject, 'updateLastMod' ):
			containedObject.updateLastMod()
		# OK, now that we've got an object, start firing events
		lifecycleevent.created( containedObject )
		try:
			owner.addContainedObject( containedObject ) # Should fire lifecycleevent.added
		except KeyError:
			# for ease of testing, re-posting with an exported data file,
			# try to auto-gen an ID.
			logger.debug( "Sent ID of existing object, ignoring", exc_info=True )
			try:
				containedObject.id = None
			except AttributeError:
				# It's valid to not be able to assign to the ID attribute; it must
				# be given at creation time and never after (think immutable usernames
				# which must not overlap and cannot be auto-generated). In that case,
				# there's nothing else we can do but inform the client
				transaction.doom()
				raise hexc.HTTPConflict("Cannot use an ID already in use")
			else:
				owner.addContainedObject( containedObject )

		self.request.response.status_int = 201

		# Respond with the generic location of the object, within
		# the owner's Objects tree.
		self.request.response.location = self.request.resource_url( owner,
																	'Objects',
																	toExternalOID( containedObject ) )

		containerId = getattr( containedObject, StandardInternalFields.CONTAINER_ID, None )
		# I think this log message should be info not debug.  It exists to provide statistics not to debug.
		logger.info("User '%s' created object '%s'/'%s' for container '%s'", creator, containedObject.id, type(containedObject).__name__, containerId)

		__traceback_info__ = containedObject
		assert containedObject.__parent__
		assert containedObject.__name__

		# We used to ACL proxy here
		return containedObject

class UGDDeleteView(AbstractAuthenticatedView,ModeledContentEditRequestUtilsMixin):
	""" DELETing an existing object is possible. Only the user
	that owns the object can DELETE it."""

	def __call__(self):
		context = self.request.context
		theObject = getattr( context, 'resource', context ) # TODO: b/w/c that can vanish. just context.
		self._check_object_exists( theObject )

		user = theObject.creator

		self._check_object_exists( theObject )

		objectId = theObject.id
		if self._do_delete_object( theObject )  is None: # Should fire lifecycleevent.removed
			raise hexc.HTTPNotFound()

		lastModified = theObject.creator.lastModified

		# TS thinks this log message should be info not debug.  It exists to provide statistics not to debug.
		logger.info("User '%s' deleted object '%s'/'%s' from container '%s'", user, objectId, getattr(theObject,'__class__', type(theObject)).__name__, theObject.containerId)

		result = hexc.HTTPNoContent()
		result.last_modified = lastModified
		return result

	def _do_delete_object( self, theObject ):
		return theObject.creator.deleteContainedObject( theObject.containerId, theObject.id )

class UGDPutView(AbstractAuthenticatedView,ModeledContentUploadRequestUtilsMixin,ModeledContentEditRequestUtilsMixin):
	""" PUTting to an existing object is possible (but not
	creating an object with an arbitrary OID)."""


	def _get_object_to_update( self ):
		try:
			return self.request.context.resource
		except AttributeError:
			# TODO: Legacy compat. The 'resource' property is deprecated
			if nti_interfaces.IZContained.providedBy( self.request.context ):
				return self.request.context
			raise

	def __call__(self):
		object_to_update = self._get_object_to_update()
		theObject = object_to_update
		self._check_object_exists( theObject )

		# Then ensure the users match
		# remoteUser = self.getRemoteUser()
		# if remoteUser != theObject.creator:
		# 	raise hexc.HTTPForbidden()

		creator = theObject.creator
		containerId = theObject.containerId
		objId = theObject.id

		externalValue = self.readInput( )

		self._check_object_exists( theObject, creator, containerId, objId )

		self.updateContentObject( theObject, externalValue ) # Should fire lifecycleevent.modified

		# TS thinks this log message should be info not debug.  It exists to provide statistics not to debug.
		logger.info("User '%s' updated object '%s'/'%s' for container '%s'", creator, theObject.id, getattr(theObject,'__class__',type(theObject)).__name__, containerId)

		if theObject and theObject == theObject.creator:
			# Updating a user. Naturally, this is done by
			# the user himself. We never want to send
			# back the entire user, but we do want to
			# send back the personal summary, the most
			# they ever get.
			# TODO: This should be handled by the renderer. Maybe we set
			# a name that controls the component lookup?
			theObject = toExternalObject( theObject, 'personal-summary' )
			self._check_object_exists( theObject, creator, containerId, objId )

		return theObject
		# We used to ACL proxy here, but that should no longer be necessary.

class UGDFieldPutView(UGDPutView):
	"""
	PUTting to an object with an external field mutates that object's
	field. The input data is the value of the field.
	The context is an `IExternalFieldResource`
	"""

	inputClass = object

	def readInput( self, value=None ):
		value = super(UGDFieldPutView,self).readInput(value=value)
		if self.request.context.wrap_value:
			return { self.request.context.__name__: value }
		return value
