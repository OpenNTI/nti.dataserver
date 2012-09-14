#!/usr/bin/env python
"""
Defines traversal views and resources for the dataserver.
"""
from __future__ import print_function, unicode_literals, absolute_import
logger = __import__( 'logging' ).getLogger( __name__ )

import sys
import numbers
import collections
import time

from zope import component
from zope import interface

from zope import lifecycleevent
from zope.schema import interfaces as sch_interfaces

import pyramid.security as sec
from nti.appserver import httpexceptions as hexc
from nti.appserver.httpexceptions import HTTPUnprocessableEntity

from pyramid import traversal
import transaction

from zope.location.location import LocationProxy

from nti.dataserver.interfaces import (IDataserver, ISimpleEnclosureContainer, IEnclosedContent)
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users

from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.oids import to_external_ntiid_oid as toExternalOID
from nti.externalization.interfaces import StandardInternalFields, StandardExternalFields
from nti.ntiids import ntiids

from nti.dataserver import enclosures
from nti.dataserver.mimetype import MIME_BASE, nti_mimetype_from_object
from nti.appserver import interfaces as app_interfaces

from nti.contentlibrary import interfaces as lib_interfaces
from nti.assessment import interfaces as asm_interfaces

from nti.appserver import _external_object_io as obj_io

class _ServiceGetView(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		username = sec.authenticated_userid( self.request )
		ds = self.request.registry.getUtility(IDataserver)
		user = users.User.get_user( username, dataserver=ds )
		if not user:
			raise hexc.HTTPForbidden()
		service = self.request.registry.getAdapter( user, app_interfaces.IService )
		#service.__parent__ = self.request.context
		return service


class _GenericGetView(object):

	def __init__( self, request ):
		self.request = request

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

class _EmptyContainerGetView(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		raise hexc.HTTPNotFound( self.request.context.ntiid )



import nti.externalization.internalization
def _createContentObject( dataserver, owner, datatype, externalValue, creator ):
	"""
	:param owner: The entity which will contain the object.
	:param creator: The user attempting to create the object. Possibly separate from the
		owner. Permissions will be checked for the creator
	"""
	# The datatype can legit be null if we are MimeType-only
	if externalValue is None:
		return None

	result = None
	if datatype is not None and owner is not None:
		result = owner.maybeCreateContainedObjectWithType( datatype, externalValue )

	if result is None:
		result = nti.externalization.internalization.find_factory_for( externalValue )
		if result:
			result = result()

	return result

class _UGDModifyViewBase(object):

	inputClass = dict
	def __init__( self, request ):
		self.request = request
		self.dataserver = self.request.registry.getUtility(IDataserver)


	def readInput(self, value=None):
		""" Returns the object specified by self.inputClass object. The data from the
		input stream is parsed, an instance of self.inputClass is created and update()'d
		from the input data.

		:raises hexc.HTTPBadRequest: If there is an error parsing/transforming the
			client request.
		"""
		result = obj_io.read_body_as_external_object( self.request, input_data=value, expected_type=self.inputClass )
		try:
			return self._transformInput( result )
		except hexc.HTTPException:
			raise
		except Exception:
			# Sadly, there's not a good exception list to catch.
			# plistlib raises undocumented exceptions from xml.parsers.expat
			# json may raise ValueError or other things, depending on implementation.
			# transformInput may raise TypeError if the request is bad, but it
			# may also raise AttributeError if the inputClass is bad, but that
			# could also come from other places. We call it all client error.
			logger.exception( "Failed to parse/transform value %s", value )
			_, _, tb = sys.exc_info()
			ex = hexc.HTTPBadRequest()
			raise ex, None, tb

	def getRemoteUser( self ):
		return users.User.get_user( sec.authenticated_userid( self.request ), dataserver=self.dataserver )

	def _transformInput( self, value ):
		return value

	def _check_object_exists(self, o, cr='', cid='', oid=''):
		if o is None:
			raise hexc.HTTPNotFound( "No object %s/%s/%s" % (cr, cid,oid))

	def updateContentObject( self, contentObject, externalValue, set_id=False, notify=True ):
		containedObject = obj_io.update_object_from_external_object( contentObject, externalValue, notify=notify, request=self.request )

		# If they provided an ID, use it if we can and we need to
		if set_id and StandardExternalFields.ID in externalValue \
			and hasattr( containedObject, StandardInternalFields.ID ) \
			and getattr( containedObject, StandardInternalFields.ID, None ) != externalValue[StandardExternalFields.ID]:
			try:
				containedObject.id = externalValue['ID']
			except AttributeError:
				# It's OK if we cannot use the given ID; POST is meant
				# to auto-assign
				pass
		return containedObject

	def idForLocation( self, value ):
		theId = None
		if isinstance(value,collections.Mapping):
			theId = value['ID']
		elif hasattr(value, 'id' ):
			theId = value.id
		return theId

	def _find_file_field(self):
		if self.request.content_type == 'multipart/form-data':
			# Expecting exactly one key in POST, the file
			field = None
			for k in self.request.POST:
				v = self.request.POST[k]
				if hasattr( v, 'type' ) and hasattr( v, 'file' ):
					# must be our field
					field = v
					break
			return field

	def _get_body_content(self):
		field = self._find_file_field()
		if field is not None:
			in_file = field.file
			in_file.seek( 0 )
			return in_file.read()

		return self.request.body

	def _get_body_type(self):
		field = self._find_file_field()
		if field is not None:
			return field.type
		return self.request.content_type or 'application/octet-stream'

	def _get_body_name(self):
		field = self._find_file_field()
		if field is not None and field.filename:
			return field.filename
		return self.request.headers.get( 'Slug' ) or ''


from nti.dataserver.mimetype import nti_mimetype_class

def class_name_from_content_type( request ):
	"""
	:return: The class name portion of one of our content-types, or None
		if the content-type doesn't conform. Note that this will be lowercase.
	"""
	content_type = request.content_type if hasattr( request, 'content_type' ) else request
	content_type = content_type or ''
	return nti_mimetype_class( content_type )

def _id(x): return x

def _question_submission_transformer( obj ):
	# Grade it, by adapting the object into an IAssessedQuestion
	return asm_interfaces.IQAssessedQuestion

def _question_set_submission_transformer( obj ):
	# Grade it, by adapting the object into an IAssessedQuestionSet
	return asm_interfaces.IQAssessedQuestionSet


class _UGDPostView(_UGDModifyViewBase):
	""" HTTP says POST creates a NEW entity under the Request-URI """
	# Therefore our context is a container, and we should respond created.

	def __init__( self, request ):
		super(_UGDPostView,self).__init__( request )

	def createContentObject( self, user, datatype, externalValue, creator ):
		return _createContentObject( self.dataserver, user, datatype, externalValue, creator )

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
			datatype = class_name_from_content_type( self.request )
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
				owner.addContainedObject( containedObject )
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
		return containedObject
		# We used to ACL proxy here


class _UGDDeleteView(_UGDModifyViewBase):
	""" DELETing an existing object is possible. Only the user
	that owns the object can DELETE it."""

	def __init__(self, request):
		super(_UGDDeleteView,self).__init__( request )


	def __call__(self):
		context = self.request.context
		theObject = getattr( context, 'resource', context ) # TODO: b/w/c that can vanish. just context.
		self._check_object_exists( theObject )

		user = theObject.creator
		with user.updates():
			theObject = user.getContainedObject( theObject.containerId, theObject.id )
			# FIXME: See notes in _UGDPutView

			if theObject is None:
				# See comment above about BWC
				enclosed = traversal.find_interface( getattr( self.request.context, 'resource', self.request.context ), IEnclosedContent )
				if enclosed:
					# should be self.request.context.resource.__parent__
					self.request.context = enclosed
					return _EnclosureDeleteView( self.request )()

			self._check_object_exists( theObject )

			lastModified = 0
			if user.deleteContainedObject( theObject.containerId, theObject.id ) is None:
				raise hexc.HTTPNotFound()

			lastModified = theObject.creator.lastModified

		result = hexc.HTTPNoContent()
		result.last_modified = lastModified
		return result


class _UGDPutView(_UGDModifyViewBase):
	""" PUTting to an existing object is possible (but not
	creating an object with an arbitrary OID)."""


	def __init__(self, request):
		super(_UGDPutView,self).__init__(request)

	def _get_object_to_update( self ):
		try:
			return self.request.context.resource
		except AttributeError:
			# TODO: Legacy compat. The 'resource' property is deprecated
			if nti_interfaces.IZContained.providedBy( self.request.context ):
				return self.request.context
			raise

	def __call__(self):
		context = self.request.context
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
			theObject = creator.getContainedObject( containerId, objId )
			# FIXME: This is terrible. We are dispatching again if we cannot resolve the object.
			# We would have arrived here through the 'Objects' path and found
			# (the child of) an 'enclosure' object, not an object actually contained by the user
			if theObject is None and traversal.find_interface( object_to_update, IEnclosedContent ):
				# should be self.request.context.resource.__parent__
				self.request.context = traversal.find_interface( object_to_update, IEnclosedContent )
				return _EnclosurePutView( self.request )()

			self._check_object_exists( theObject, creator, containerId, objId )

			self.updateContentObject( theObject, externalValue )


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


def _force_update_modification_time( object, lastModified, max_depth=-1 ):
	"""Traverse up the parent tree (up to `max_depth` times) updating modification times."""
	if hasattr( object, 'updateLastMod' ):
		object.updateLastMod( lastModified )

	if max_depth == 0:
		return
	if max_depth > 0:
		max_depth = max_depth - 1

	parent = getattr( object, '__parent__', None )
	if parent is None:
		return
	_force_update_modification_time( parent, lastModified, max_depth )

class _EnclosurePostView(_UGDModifyViewBase):
	"""
	View for creating new enclosures.
	"""

	def __init__(self, request):
		super(_EnclosurePostView,self).__init__( request )

	def __call__(self):
		context = self.request.context # A _AbstractObjectResource OR an ISimpleEnclosureContainer
		# Enclosure containers are defined to be IContainerNamesContainer,
		# which means they will choose their name based on what we give them
		enclosure_container = context if ISimpleEnclosureContainer.providedBy( context ) else context.resource

		# AtomPub specifies a 'Slug' header to be used as the base of the
		# name
		# TODO: Use a ZCA factory to create enclosure?

		content = None
		content_type = self._get_body_type()
		# Chop a trailing '+json' off if present
		if '+' in content_type:
			content_type = content_type[0:content_type.index('+')]

		# First, see if they're giving us something we can model
		datatype = class_name_from_content_type( content_type )
		datatype = datatype + 's' if datatype else None
		# Pass in all the information we have, as if it was a full externalized object
		modeled_content = nti.externalization.internalization.find_factory_for( {StandardExternalFields.MIMETYPE: content_type,
																				 StandardExternalFields.CLASS: datatype} )
		if modeled_content:
			modeled_content = modeled_content()
		#modeled_content = self.dataserver.create_content_type( datatype, create_missing=False )
		#if not getattr( modeled_content, '__external_can_create__', False ):
		#	modeled_content = None

		if modeled_content is not None:
			modeled_content.creator = self.getRemoteUser()
			self.updateContentObject( modeled_content, self.readInput(self._get_body_content()), set_id=True )
			modeled_content.containerId = getattr( enclosure_container, 'id', None ) or getattr( enclosure_container, 'ID' ) # TODO: Assumptions
			content_type = nti_mimetype_from_object( modeled_content )

		content = modeled_content if modeled_content is not None else self._get_body_content()
		if content is not modeled_content and content_type.startswith( MIME_BASE ):
			# If they tried to send us something to model, but we didn't actually
			# model it, then screw that, it's just a blob
			content_type = 'application/octet-stream'
			# OTOH, it would be nice to not have to
			# replicate the content type into the enclosure object when we
			# create it. We should delay until later. This means we need a new
			# enclosure object

		enclosure = enclosures.SimplePersistentEnclosure(
			self._get_body_name(),
			content,
			content_type )
		enclosure.creator = self.getRemoteUser()
		enclosure_container.add_enclosure( enclosure )

		# Ensure we'll be able to get a OID
		if getattr( enclosure_container, '_p_jar', None ):
			if modeled_content is not None:
				enclosure_container._p_jar.add( modeled_content )
			enclosure_container._p_jar.add( enclosure )

		# TODO: Creating enclosures generally doesn't update the modification time
		# of its container. It arguably should. Since we currently report a few levels
		# of the tree at once, though, (classes AND their sections) it is necessary
		# to update a few levels at once. This is wrong and increases the chance of conflicts.
		# The right thing is to stop doing that.
		_force_update_modification_time( enclosure_container, enclosure.lastModified )

		self.request.response.status_int = 201 # Created
		# If we're doing a form submission, then the browser (damn IE)
		# will try to follow this location if we send it
		# which results in annoying and useless dialogs
		if self._find_file_field() is None:
			self.request.response.location = self.request.resource_url( LocationProxy( enclosure,
																					   context,
																					   enclosure.name ) )
		# TODO: We need to return some representation of this object
		# just created. We need an 'Entry' wrapper.
		#return ACLLocationProxy( enclosure, context, enclosure.name, nacl.ACL( enclosure, context.__acl__ ) )
		return enclosure

class _EnclosurePutView(_UGDModifyViewBase):
	"""
	View for editing an existing enclosure.
	"""

	def __init__( self, request ):
		super(_EnclosurePutView,self).__init__( request )

	def __call__( self ):
		context = self.request.context
		assert IEnclosedContent.providedBy( context )


		# How should we be dealing with changes to Content-Type?
		# Changes to Slug are not allowed because that would change the URL
		# Not modeled # TODO: Check IModeledContent.providedBy( context.data )?
		# FIXME: See comments in _EnclosurePostView about mod times.
		if not context.mime_type.startswith( MIME_BASE ):
			context.data = self._get_body_content()
			_force_update_modification_time( context, time.time() )
			result = hexc.HTTPNoContent()
		else:
			modeled_content = context.data
			self.updateContentObject( modeled_content, self.readInput(self._get_body_content()) )
			result = modeled_content
			_force_update_modification_time( context, modeled_content.lastModified )
		return result

class _EnclosureDeleteView(object):
	"""
	View for deleting an object.
	"""

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		context = self.request.context
		assert IEnclosedContent.providedBy( context )
		container = traversal.find_interface( context, ISimpleEnclosureContainer )
		# TODO: Handle the KeyError here and also if ISimpleEnclosureContainer was not found
		container.del_enclosure( context.name )

		result = hexc.HTTPNoContent()
		return result

def _method_not_allowed(request):
	raise hexc.HTTPMethodNotAllowed()

def _provider_redirect_classes(request):
	class_path = (request.path + '/Classes') + (('?' + request.query_string) if request.query_string else '')
	raise hexc.HTTPFound(location=class_path)
