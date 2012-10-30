#!/usr/bin/env python
"""
Defines traversal views and resources for the dataserver.
"""
from __future__ import print_function, unicode_literals, absolute_import
logger = __import__( 'logging' ).getLogger( __name__ )


from zope import component
from zope import interface

from zope import lifecycleevent
from zope.schema import interfaces as sch_interfaces


from nti.appserver import httpexceptions as hexc
from nti.appserver.httpexceptions import HTTPUnprocessableEntity

from pyramid import traversal
import transaction

from zope.location.location import LocationProxy

from nti.dataserver.interfaces import IEnclosedContent
from nti.dataserver import interfaces as nti_interfaces


from nti.externalization.externalization import toExternalObject

from nti.externalization.oids import to_external_ntiid_oid as toExternalOID
from nti.externalization.interfaces import StandardInternalFields

from nti.appserver import interfaces as app_interfaces
from nti.assessment import interfaces as asm_interfaces

from nti.appserver import _external_object_io as obj_io
from nti.appserver._view_utils import ModeledContentUploadRequestUtilsMixin
from nti.appserver._view_utils import ModeledContentEditRequestUtilsMixin
from nti.appserver._view_utils import AbstractAuthenticatedView
from nti.appserver._view_utils import AbstractView

from nti.appserver.enclosure_views import EnclosureDeleteView
from nti.appserver.enclosure_views import EnclosurePutView

class _ServiceGetView(AbstractAuthenticatedView):

	def __call__( self ):
		user = self.getRemoteUser()
		if not user:
			raise hexc.HTTPForbidden()
		service = self.request.registry.getAdapter( user, app_interfaces.IService )
		#service.__parent__ = self.request.context
		return service


class _GenericGetView(AbstractView):

	def __call__( self ):
		# TODO: We sometimes want to change the interface that we return
		# We're doing this to turn a dataserver IContainer (which externalizes poorly)
		# to an ICollection (which externalizes nicely.) How to make this
		# configurable/generic?
		# For right now, we're looking for an adapter registered with the name of the
		# last component we traversed, and then falling back to the default

		# TODO: Assuming the result that we get is some sort of container,
		# then we're leaving the renderer to insert next/prev first/last related
		# links and handle paging. Is that right?
		# NOTE: We'll take either one of the wrapper classes defined
		# in this module, or the object itself
		resource = getattr( self.request.context, 'resource', self.request.context )
		result = component.queryAdapter( resource,
										 app_interfaces.ICollection,
										 name=self.request.traversed[-1] )
		if not result:
			result = component.queryAdapter( resource,
											 app_interfaces.ICollection,
											 default=resource )
		if hasattr( result, '__parent__' ):
			# FIXME: Choosing which parent to set is also borked up.
			# Some context objects (resources) are at the same conceptual level
			# as the actual request.context, some are /beneath/ that level??
			# If we have a link all the way back up to the root, we're good?
			# TODO: This can probably mostly go away now?
			if result is resource:
				# Must be careful not to modify the persistent object
				result = LocationProxy( result, getattr( result, '__parent__', None), getattr( result, '__name__', None ) )
			if getattr( resource, '__parent__', None ) is not None:
				result.__parent__ = resource.__parent__
				# FIXME: Another hack at getting the right parent relationship in.
				# The actual parent relationship is to the Provider object,
				# but it has no way back to the root resource. This hack is deliberately
				# kept very specific for now.
				if self.request.traversed[-1] == 'Classes' and self.request.traversed[0] == 'providers':
					result.__parent__ = self.request.context.__parent__
				elif self.request.traversed[-1] == 'Pages' and self.request.traversed[0] == 'users':
					result.__parent__ = self.request.context.__parent__
			elif resource is not self.request.context and hasattr( self.request.context, '__parent__' ):
				result.__parent__ = self.request.context.__parent__
		return result

class _EmptyContainerGetView(AbstractView):

	def __call__( self ):
		raise hexc.HTTPNotFound( self.request.context.ntiid )


def _id(x): return x

def _question_submission_transformer( obj ):
	# Grade it, by adapting the object into an IAssessedQuestion
	return asm_interfaces.IQAssessedQuestion

def _question_set_submission_transformer( obj ):
	# Grade it, by adapting the object into an IAssessedQuestionSet
	return asm_interfaces.IQAssessedQuestionSet


class _UGDPostView(AbstractAuthenticatedView,ModeledContentUploadRequestUtilsMixin):
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
		creator = self.getRemoteUser()
		context = self.request.context
		# If our context contains a user resource, then that's where we should be trying to
		# create things
		owner_root = traversal.find_interface( context, app_interfaces.IUserResource )
		if owner_root is not None:
			owner_root = getattr( owner_root, 'user', owner_root ) # migration compat
		if owner_root is None:
			owner_root = traversal.find_interface( context, nti_interfaces.IUser )
		if owner_root is None and hasattr( context, 'container' ):
			owner_root = traversal.find_interface( context.container, nti_interfaces.IUser )

		owner = owner_root if owner_root else creator
		externalValue = self.readInput()
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
		if containedObject is None:
			transaction.doom()
			logger.debug( "Failing to POST: input of unsupported/missing Class: %s %s", datatype, externalValue )
			raise hexc.HTTPUnprocessableEntity( 'Unsupported/missing Class' )

		with owner.updates():
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
				if getattr( containedObject, StandardInternalFields.CONTAINER_ID, None ) \
				  and not getattr( transformedObject, StandardInternalFields.CONTAINER_ID, None ):
				  transformedObject.containerId = containedObject.containerId
				  # TODO: JAM: I really don't like doing this. Straighten out the
				  # location of IContained so that things like assessment can implement it
				  if not nti_interfaces.IContained.providedBy( transformedObject ):
					  interface.alsoProvides( transformedObject, nti_interfaces.IContained )
				containedObject = transformedObject
			# TODO: The WSGI code would attempt to infer a containerID from the
			# path. Should we?
			if not getattr( containedObject, StandardInternalFields.CONTAINER_ID, None ):
				transaction.doom()
				logger.debug( "Failing to POST: input of unsupported/missing ContainerId" )
				raise HTTPUnprocessableEntity( "Unsupported/missing ContainerId" )

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

		__traceback_info__ = containedObject
		assert containedObject.__parent__
		assert containedObject.__name__

		# We used to ACL proxy here
		return containedObject



class _UGDDeleteView(AbstractAuthenticatedView,ModeledContentEditRequestUtilsMixin):
	""" DELETing an existing object is possible. Only the user
	that owns the object can DELETE it."""

	def __call__(self):
		context = self.request.context
		theObject = getattr( context, 'resource', context ) # TODO: b/w/c that can vanish. just context.
		self._check_object_exists( theObject )

		user = theObject.creator
		with user.updates():
			theObject = self.checkObjectOutFromUserForUpdate( user, theObject.containerId, theObject.id )
			# FIXME: See notes in _UGDPutView

			if theObject is None:
				# See comment above about BWC
				enclosed = traversal.find_interface( getattr( self.request.context, 'resource', self.request.context ), IEnclosedContent )
				if enclosed:
					# should be self.request.context.resource.__parent__
					self.request.context = enclosed
					return EnclosureDeleteView( self.request )()

			self._check_object_exists( theObject )

			lastModified = 0
			if user.deleteContainedObject( theObject.containerId, theObject.id ) is None: # Should fire lifecycleevent.removed
				raise hexc.HTTPNotFound()

			lastModified = theObject.creator.lastModified

		result = hexc.HTTPNoContent()
		result.last_modified = lastModified
		return result


class _UGDPutView(AbstractAuthenticatedView,ModeledContentUploadRequestUtilsMixin,ModeledContentEditRequestUtilsMixin):
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
		with creator.updates():
			# Check the object out from the user now so that
			# it goes through the right update processes (in particular,
			# that it will cache the right sharing values)
			# TODO: This is sort of weird. Have User.willUpdate and User.didUpdate
			# to be explicit?
			theObject = self.checkObjectOutFromUserForUpdate( creator, containerId, objId )
			# FIXME: This is terrible. We are dispatching again if we cannot resolve the object.
			# We would have arrived here through the 'Objects' path and found
			# (the child of) an 'enclosure' object, not an object actually contained by the user
			if theObject is None and traversal.find_interface( object_to_update, IEnclosedContent ):
				# should be self.request.context.resource.__parent__
				self.request.context = traversal.find_interface( object_to_update, IEnclosedContent )
				return EnclosurePutView( self.request )()

			self._check_object_exists( theObject, creator, containerId, objId )

			self.updateContentObject( theObject, externalValue ) # Should fire lifecycleevent.modified


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


class _UGDFieldPutView(_UGDPutView):
	"""
	PUTting to an object with an external field mutates that object's
	field. The input data is the value of the field.
	The context is an `IExternalFieldResource`
	"""

	inputClass = object

	def readInput( self, value=None ):
		value = super(_UGDFieldPutView,self).readInput(value=value)
		if self.request.context.wrap_value:
			return { self.request.context.__name__: value }
		return value



def _method_not_allowed(request):
	raise hexc.HTTPMethodNotAllowed()

def _provider_redirect_classes(request):
	class_path = (request.path + '/Classes') + (('?' + request.query_string) if request.query_string else '')
	raise hexc.HTTPFound(location=class_path)
