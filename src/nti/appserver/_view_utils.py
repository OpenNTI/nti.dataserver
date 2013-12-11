#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities relating to views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import datetime
import transaction

try:
	from Acquisition import aq_base
except ImportError: #PyPy?
	def aq_base(o): return o

from zope import interface
from zope import component
from zope.cachedescriptors.property import Lazy
from zope.schema import interfaces as sch_interfaces

from pyramid.threadlocal import get_current_request
from pyramid import traversal
import webob.datetime_utils

from nti.appserver import httpexceptions as hexc
from nti.appserver import interfaces as app_interfaces
from nti.appserver import _external_object_io as obj_io

from nti.dataserver import users
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IUser

from nti.externalization.interfaces import StandardInternalFields, StandardExternalFields
from nti.externalization.externalization import to_standard_external_last_modified_time
from nti.mimetype import mimetype


def get_remote_user(request=None, dataserver=None):
	"""
	Returns the user object corresponding to the authenticated user of the
	request, or None (if there is no request or no dataserver or no such user)
	"""
	request = request or get_current_request()
	dataserver = dataserver or component.queryUtility( IDataserver )

	result = None
	if request is not None and dataserver is not None:
		result = users.User.get_user(request.authenticated_userid, dataserver=dataserver)
	return result

class AbstractView(object):
	"""
	Base class for views. Defines the ``request`` and ``dataserver`` property.
	"""
	def __init__(self, request):
		self.request = request
		self.dataserver = component.getUtility(IDataserver)

class AbstractAuthenticatedView(AbstractView):
	"""
	Base class for views that expect authentication to be required.
	"""

	def getRemoteUser( self ):
		"""
		Returns the user object corresponding to the currently authenticated
		request.
		"""
		return get_remote_user( self.request, self.dataserver )

	@Lazy
	def remoteUser(self):
		"""
		Returns the remote user for the current request; cached on first use.
		"""
		return self.getRemoteUser()

class UploadRequestUtilsMixin(object):
	"""
	A mixin class that can be added to view classes to provide
	utility methods for working with the content of uploads, especially
	useful for supporting different types of uploads. The subclass must
	define the ``request`` attribute.
	"""

	request = None

	def _find_file_field(self):
		"""
		Find the object representing the file upload portion of a form POST (or PUT).
		Assumes there is only one, and if one is found it is returned. Otherwise
		None is returned.
		:return: An instance of :class:`cgi.FieldStorage` or None.
		"""
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
		"""
		Return the uploaded body content for the current request as a byte string.
		This will either be the POST'd file data, or the request body.
		"""
		field = self._find_file_field()
		if field is not None:
			in_file = field.file
			in_file.seek( 0 )
			return in_file.read()

		return self.request.body

	def _get_body_type(self):
		"""
		Returns a string giving the MIME type of the uploaded
		body (either the POST'd file or the request itself). If
		no type is given by the client, returns a generic type.
		"""
		field = self._find_file_field()
		if field is not None:
			return field.type
		return self.request.content_type or b'application/octet-stream'

	def _get_body_name(self):
		"""
		Returns a string giving the name that the client would like to use
		for the uploaded body. This will either be the file name sent
		in the POST request, or the AtomPub ``Slug`` header. If no name
		is found, then an empty string is returned.
		"""
		field = self._find_file_field()
		if field is not None and field.filename:
			return field.filename
		return self.request.headers.get( 'Slug' ) or ''

class ModeledContentUploadRequestUtilsMixin(object):
	"""
	A mixin class that can be added to views to help working with
	uploading content that is parsed and treated as modeled content.
	The subclass defines the ``request`` attribute.
	"""

	inputClass = dict
	content_predicate = id

	def __call__( self ):
		"""
		Subclasses may implement a `_do_call` method if they do not override
		__call__.
		"""
		try:
			return self._do_call()
		except sch_interfaces.ValidationError as e:
			obj_io.handle_validation_error( self.request, e )
		except interface.Invalid as e:
			obj_io.handle_possible_validation_error( self.request, e )

	def readInput(self, value=None):
		"""
		Returns the object specified by self.inputClass object. The data from the
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

	def _transformInput( self, value ):
		return value

	def findContentType( self, externalValue ):
		"""
		Attempts to find the best content type (datatype), one that can be used with
		:meth:`createContentObject`.

		There are multiple places this can come from. In priority order, they are:

		* The ``MimeType`` value in the given data;
		* The ``ContentType`` header, if it names an NTI content type (any trailing +json will be removed);
		* Last, the ``Class`` value in the given data

		Note that this method can return either a simple class name, or a Mime type
		string.
		"""

		if externalValue.get( 'MimeType' ):
			return externalValue['MimeType']

		if self.request.content_type and self.request.content_type.startswith( mimetype.MIME_BASE ):
			datatype = self.request.content_type
			if datatype.endswith( '+json' ):
				datatype = datatype[:-5] # strip +json
			if datatype and datatype != mimetype.MIME_BASE: # prevent taking just the base type
				return datatype

		if externalValue.get( 'Class' ):
			return externalValue['Class'] + 's'


	def createContentObject( self, user, datatype, externalValue, creator ):
		return obj_io.create_modeled_content_object( self.dataserver, user, datatype, externalValue, creator )

	def createAndCheckContentObject( self, owner, datatype, externalValue, creator, predicate=None ):
		if predicate is None:
			predicate = self.content_predicate
		containedObject = self.createContentObject( owner, datatype, externalValue, creator )
		if containedObject is None or not predicate(containedObject):
			transaction.doom()
			logger.debug( "Failing to POST: input of unsupported/missing Class: %s %s", datatype, externalValue )
			raise hexc.HTTPUnprocessableEntity( 'Unsupported/missing Class' )
		return containedObject

	def updateContentObject( self, contentObject, externalValue, set_id=False, notify=True ):
		# We want to be sure to only change values on the actual content object,
		# not things in its traversal lineage
		containedObject = obj_io.update_object_from_external_object( aq_base(contentObject), externalValue, notify=notify, request=self.request )

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

	def readCreateUpdateContentObject( self, user, search_owner=False  ):
		"""
		Combines reading the external input, deriving the expected data
		type, creating the content object, and updating it in one step.

		:keyword bool search_owner: If set to True (not the default), we will
			look for a user along our context's lineage; the user
			will be used by default. It will be returned. If False,
			the return will only be the contained object.

		"""
		creator = user
		externalValue = self.readInput()
		datatype = self.findContentType( externalValue )

		context = self.request.context
		# If our context contains a user resource, then that's where we should be trying to
		# store things. This may be different than the creator if the remote
		# user is an administrator (TODO: Revisit this.)
		owner_root = None
		if search_owner:
			owner_root = traversal.find_interface( context, IUser )
			if owner_root is not None:
				owner_root = getattr( owner_root, 'user', owner_root ) # migration compat
			if owner_root is None:
				owner_root = traversal.find_interface( context, IUser )
			if owner_root is None and hasattr( context, 'container' ):
				owner_root = traversal.find_interface( context.container, IUser )

		owner = owner_root if owner_root else creator

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

		return (containedObject, owner) if search_owner else containedObject


class ModeledContentEditRequestUtilsMixin(object):
	"""
	A mixin class that can be added to views that are editing new
	or existing objects.
	"""

	def _check_object_exists(self, o, cr='', cid='', oid=''):
		"""
		If the first argument is None or has been deleted (is marked
		with :class:`IDeletedObjectPlaceholder`), raises a 404 error.
		The remaining arguments are used as details in the message.
		"""
		if o is None or app_interfaces.IDeletedObjectPlaceholder.providedBy( o ):
			raise hexc.HTTPNotFound( "No object %s/%s/%s" % (cr, cid,oid))

	def _check_object_unmodified_since( self, obj ):
		"""
		If the request for this object has a 'If-Unmodified-Since' header,
		and the provided object supports modification times, then the two
		values will be compared, and if the objects modification time is
		more recent than the request's, HTTP's 412 Precondition failed will be
		raised.
		"""

		if self.request.if_unmodified_since is not None:
			obj_last_mod = to_standard_external_last_modified_time( obj )
			if obj_last_mod is not None \
				and datetime.datetime.fromtimestamp( obj_last_mod, webob.datetime_utils.UTC ) > self.request.if_unmodified_since:
				raise hexc.HTTPPreconditionFailed()
