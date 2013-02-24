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

import transaction
from Acquisition import aq_base
from zope import interface
from zope import component

from pyramid.interfaces import IRequest
from pyramid import security as sec

from nti.dataserver.interfaces import IDataserver
from nti.dataserver import users

from nti.appserver import interfaces as app_interfaces
from nti.appserver import _external_object_io as obj_io
from nti.appserver import httpexceptions as hexc

from zope.schema import interfaces as sch_interfaces
from nti.externalization.interfaces import StandardInternalFields, StandardExternalFields

def get_remote_user( request, dataserver=None ):
	"""
	Returns the user object corresponding to the authenticated user of the
	request, or None.
	"""
	dataserver = dataserver or request.registry.getUtility( IDataserver )
	return users.User.get_user( sec.authenticated_userid( request ), dataserver=dataserver )

class AbstractView(object):
	"""
	Base class for views. Defines the ``request`` and ``dataserver`` property.
	"""

	def __init__( self, request ):
		self.request = request
		self.dataserver = self.request.registry.getUtility(IDataserver)

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

	def __call__( self ):
		"""
		Subclasses may implement a `_do_call` method if they do not override
		__call__.
		"""
		try:
			return self._do_call()
		except sch_interfaces.ValidationError as e:
			obj_io.handle_validation_error( self.request, e )

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
		datatype = None
		# TODO: Which should have priority, class in the data,
		# or mime-type in the headers (or data?)?
		if 'Class' in externalValue and externalValue['Class']:
			# Convert unicode to ascii
			datatype = str( externalValue['Class'] ) + 's'
		else:
			datatype = obj_io.class_name_from_content_type( self.request )
			datatype = datatype + 's' if datatype else None
		return datatype

	def createContentObject( self, user, datatype, externalValue, creator ):
		return obj_io.create_modeled_content_object( self.dataserver, user, datatype, externalValue, creator )

	def createAndCheckContentObject( self, owner, datatype, externalValue, creator, predicate=None ):
		containedObject = self.createContentObject( owner, datatype, externalValue, creator )
		if containedObject is None or (predicate and not predicate(containedObject)):
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

class ModeledContentEditRequestUtilsMixin(object):
	"""
	A mixin class that can be added to views that are editing new
	or existing objects.
	"""

	def _check_object_exists(self, o, cr='', cid='', oid=''):
		"""
		If the first argument is None, raises a 404 error. The remaining arguments
		are used as details in the message.
		"""
		if o is None:
			raise hexc.HTTPNotFound( "No object %s/%s/%s" % (cr, cid,oid))


	def checkObjectOutFromUserForUpdate( self, user, containerId, objId ):
		"""
		Having identified an object, make sure the user is aware that we are going
		to change it. Should be called in a ``with user.updates()`` block.
		"""
		# TODO: We might need to do some ID massaging here, if the ID is an OID in the old, non-intid
		# appended form
		return _default_check_object_out_from_user_for_update( self.request.context, self.request,
															   user, containerId, objId )

def _default_check_object_out_from_user_for_update( context, request, user, containerId, objId ):
	checkout = component.queryMultiAdapter( (context, request),
											app_interfaces.IUserCheckout )
	if checkout:
		return checkout.checkObjectOutFromUserForUpdate( user, containerId, objId )

	return user.getContainedObject( containerId, objId )

@interface.implementer(app_interfaces.IUserCheckout)
@component.adapter(app_interfaces.IExternalFieldResource, IRequest)
class DispatchingExternalFieldResourceCheckout(object):
	"""
	If we are wrapping a resource, we want to try to check it out directly.
	"""

	def __init__( self, context, request ):
		self.context = context
		self.request = request

	def checkObjectOutFromUserForUpdate( self, user, containerId, objId ):
		return _default_check_object_out_from_user_for_update( self.context.context, self.request,
															   user, containerId, objId )
