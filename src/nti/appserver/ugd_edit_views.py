#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User-generated data CRUD functions.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

import transaction

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.container.interfaces import InvalidContainerType

from nti.app.base.abstract_views import get_source
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.internalization import read_body_as_external_object

from nti.app.externalization.view_mixins import ModeledContentEditRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.appserver import MessageFactory as _
from nti.appserver import httpexceptions as hexc

from nti.appserver.interfaces import INewObjectTransformer

from nti.dataserver.interfaces import IContained
from nti.dataserver.interfaces import IZContained
from nti.dataserver.interfaces import IContainerContext

from nti.externalization.interfaces import StandardInternalFields
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.externalization import toExternalObject

from nti.ntiids.oids import to_external_ntiid_oid as toExternalOID

def _id(x):
	return x

class UGDPostView(AbstractAuthenticatedView,
				  ModeledContentUploadRequestUtilsMixin):
	"""
	HTTP says POST creates a NEW entity under the Request-URI
	"""

	# Therefore our context is a container, and we should respond created.

	def doReadCreateUpdateContentObject(self, creator, search_owner=True, externalValue=None):
		return super(UGDPostView, self).readCreateUpdateContentObject(creator,
																	  search_owner=search_owner,
																	  externalValue=externalValue)

	def readCreateUpdateContentObject(self, creator, search_owner=True, externalValue=None):
		if not self.request.POST:
			result = self.doReadCreateUpdateContentObject(creator,
														  search_owner=search_owner,
														  externalValue=externalValue)
		else:
			if not externalValue:
				# XXX: iPad app post objects as a multipart/form-data using
				# the 'json' field
				externalValue = get_source(self.request, 'json')

			if not externalValue:
				# read fields in multipart data
				externalValue = read_body_as_external_object(self.request)

			if not externalValue:
				raise hexc.HTTPUnprocessableEntity("No input source was specified")

			result = self.doReadCreateUpdateContentObject(creator,
													  	  search_owner=search_owner,
													      externalValue=externalValue)
		return result

	def _transform_incoming_object(self, containedObject):
		try:
			transformer = component.queryMultiAdapter((self.request, containedObject),
													   INewObjectTransformer)
			if transformer is None:
				transformer = component.queryAdapter(containedObject,
													  INewObjectTransformer,
													  default=_id)

			transformedObject = transformer(containedObject)

		except (TypeError, ValueError, AssertionError, KeyError) as e:
			transaction.doom()
			logger.warn("Failed to transform incoming object", exc_info=True)
			raise hexc.HTTPUnprocessableEntity(e.message)

		# If we transformed, copy the container and creator
		if transformedObject is not containedObject:
			transformedObject.creator = containedObject.creator
			if 		getattr(containedObject, StandardInternalFields.CONTAINER_ID, None) \
				and not getattr(transformedObject, StandardInternalFields.CONTAINER_ID, None):
				transformedObject.containerId = containedObject.containerId
				# TODO: JAM: I really don't like doing this. Straighten out the
				# location of IContained so that things like assessment can implement it
				if not IContained.providedBy(transformedObject):
					interface.alsoProvides(transformedObject, IContained)
			containedObject = transformedObject

		return containedObject

	def _do_call(self):
		creator = self.remoteUser

		if not creator:
			raise hexc.HTTPForbidden()

		containedObject, owner = self.readCreateUpdateContentObject(creator, search_owner=True)
		containedObject = self._transform_incoming_object(containedObject)
		# TODO: The WSGI code would attempt to infer a containerID from the
		# path. Should we?
		if not getattr(containedObject, StandardInternalFields.CONTAINER_ID, None):
			transaction.doom()
			logger.debug("Failing to POST: input of unsupported/missing ContainerId")
			e = InvalidContainerType("Unsupported/missing ContainerId",
									 StandardExternalFields.CONTAINER_ID, None)
			e.field = IContained['containerId']
			raise e

		if hasattr(containedObject, 'updateLastMod'):
			containedObject.updateLastMod()

		# OK, now that we've got an object, start firing events
		lifecycleevent.created(containedObject)
		try:
			owner.addContainedObject(containedObject)  # Should fire lifecycleevent.added
		except KeyError:
			# for ease of testing, re-posting with an exported data file,
			# try to auto-gen an ID.
			logger.debug("Sent ID of existing object, ignoring", exc_info=True)
			try:
				containedObject.id = None
			except AttributeError:
				# It's valid to not be able to assign to the ID attribute; it must
				# be given at creation time and never after (think immutable usernames
				# which must not overlap and cannot be auto-generated). In that case,
				# there's nothing else we can do but inform the client
				transaction.doom()
				raise hexc.HTTPConflict(_("Cannot use an ID already in use"))
			else:
				owner.addContainedObject(containedObject)

		self.request.response.status_int = 201

		# Respond with the generic location of the object, within
		# the owner's Objects tree.
		# TODO: Shouldn't this be the external OID NTIID ?
		self.request.response.location = self.request.resource_url(owner,
																   'Objects',
																   toExternalOID(containedObject))

		containerId = getattr(containedObject, StandardInternalFields.CONTAINER_ID, None)
		# I think this log message should be info not debug.  It exists to provide statistics not to debug.
		logger.info("User '%s' created object '%s'/'%s' for container '%s'",
					creator, containedObject.id,
					type(containedObject).__name__, containerId)

		__traceback_info__ = containedObject
		assert containedObject.__parent__
		assert containedObject.__name__
		# We used to ACL proxy here
		return containedObject

class ContainerContextUGDPostView(UGDPostView):
	"""
	A subclass of ``UGDPostView`` that injects a context_id on
	the inbound object, if applicable. Useful for determining
	where the object was created contextually.

	Reading/Editing/Deleting will remain the same.
	"""

	def _transform_incoming_object(self, containedObject):
		obj = super(ContainerContextUGDPostView, self)._transform_incoming_object(containedObject)
		container_context = IContainerContext(obj, None)
		if container_context:
			container_context.context_id = toExternalOID(self.context)
		return obj

class UGDDeleteView(AbstractAuthenticatedView,
					ModeledContentEditRequestUtilsMixin):
	"""
	DELETing an existing object is possible. Only the user that owns
	the object can DELETE it.
	"""

	def _get_object_to_delete(self):
		context = self.request.context
		theObject = getattr(context, 'resource', context)  # TODO: b/w/c that can vanish. just context.
		return theObject

	def __call__(self):
		theObject = self._get_object_to_delete()
		self._check_object_exists(theObject)

		# Now that we know we've got an object, see if they sent
		# preconditions
		self._check_object_unmodified_since(theObject)

		if self._do_delete_object(theObject) is None:  # Should fire lifecycleevent.removed
			raise hexc.HTTPNotFound()

		# TS thinks this log message should be info not debug.  
		# It exists to provide statistics not to debug.
		logger.info("User '%s' deleted object '%s'/'%s' from container '%s'",
					getattr(theObject, 'creator', None),
					getattr(theObject, 'id', None),
					getattr(theObject, '__class__', type(theObject)).__name__,
					getattr(theObject, 'containerId', getattr(theObject, '__parent__', None)))

		result = hexc.HTTPNoContent()
		result.last_modified = time.time()
		return result

	def _do_delete_object(self, theObject):
		"""
		Delete the object, firing an :class:`.IObjectRemovedEvent`.

		:return: Typically the object, if it was successfully deleted. If you
			return `None` (note, not a false value), then a :class:`.HTTPNotFound`
			error will be raised.
		"""
		result = theObject.creator.deleteContainedObject(theObject.containerId, theObject.id)
		return result

class UGDPutView(AbstractAuthenticatedView,
				 ModeledContentUploadRequestUtilsMixin,
				 ModeledContentEditRequestUtilsMixin):
	""" PUTting to an existing object is possible (but not
	creating an object with an arbitrary OID)."""


	def _get_object_to_update(self):
		try:
			return self.request.context.resource
		except AttributeError:
			# TODO: Legacy compat. The 'resource' property is deprecated
			if IZContained.providedBy(self.request.context):
				return self.request.context
			raise

	def __call__(self):
		object_to_update = self._get_object_to_update()
		theObject = object_to_update
		self._check_object_exists(theObject)

		# Now that we know we've got an object, see if they sent
		# preconditions
		self._check_object_unmodified_since(theObject)

		# Now check any object constraints
		externalValue = self.readInput()
		self._check_object_constraints(theObject, externalValue)

		# Then ensure the users match
		# remoteUser = self.getRemoteUser()
		# if remoteUser != theObject.creator:
		# 	raise hexc.HTTPForbidden()
		creator = theObject.creator
		# This is required; only register this view for objects that have it.
		# This class is NOT meant to be a fully generic PUT view by itself.
		# (TODO: Our registrations in application.py are wrong (zope's IContained), make them
		# more specific. Also, we could check and refuse to execute if there is a
		# subpath, view names, or query params, that was unconsumed.
		# Now experementing with using dataserver's IModeledContent which is actually correct)
		containerId = getattr(theObject, 'containerId', None)
		objectId = getattr(theObject, 'id', None) or str(theObject)

		self.updateContentObject(theObject, externalValue)  # Should fire lifecycleevent.modified

		if containerId:
			# TS thinks this log message should be info not debug.  It exists to provide
			# statistics not to debug.
			logger.info("User '%s' updated object '%s'/'%s' for container '%s'", creator,
						objectId,
						getattr(theObject, '__class__', type(theObject)).__name__,
						containerId)
		else:
			logger.info("User '%s' updated object '%s'/'%s'", creator,
						objectId,
						getattr(theObject, '__class__', type(theObject)).__name__)

		if theObject and theObject == creator:
			# Updating a user. Naturally, this is done by
			# the user himself. We never want to send
			# back the entire user, but we do want to
			# send back the personal summary, the most
			# they ever get.
			# TODO: This should be handled by the renderer. Maybe we set
			# a name that controls the component lookup?
			theObject = toExternalObject(theObject, 'personal-summary')
			# used to call self._check_object_exists, but this is a programming problem
			assert theObject is not None
		return theObject
		# We used to ACL proxy here, but that should no longer be necessary.

class UGDFieldPutView(UGDPutView):
	"""
	PUTting to an object with an external field mutates that object's
	field. The input data is the value of the field.
	The context is an `IExternalFieldResource`
	"""

	inputClass = object

	def readInput(self, value=None):
		value = super(UGDFieldPutView, self).readInput(value=value)
		if self.request.context.wrap_value:
			return { self.request.context.__name__: value }
		return value
