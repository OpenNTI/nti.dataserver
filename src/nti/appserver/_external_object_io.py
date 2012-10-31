#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support functions for object IO.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections
import sys
import simplejson

from zope import component
from zope import interface
import zope.schema.interfaces
from zope.i18n import translate
from z3c.password import interfaces as pwd_interfaces

from pyramid.threadlocal import get_current_request

from nti.appserver import httpexceptions as hexc
from nti.appserver._util import raise_json_error

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.mimetype import nti_mimetype_class
import nti.externalization.internalization


def create_modeled_content_object( dataserver, owner, datatype, externalValue, creator ):
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



def class_name_from_content_type( request ):
	"""
	:return: The class name portion of one of our content-types, or None
		if the content-type doesn't conform. Note that this will be lowercase.
	"""
	content_type = request.content_type if hasattr( request, 'content_type' ) else request
	content_type = content_type or ''
	return nti_mimetype_class( content_type )


def read_body_as_external_object( request, input_data=None, expected_type=collections.Mapping ):
	"""
	Returns the object specified by the external data. The request input stream is
	input stream is parsed, and the return value is verified to be of `expected_type`

	:param input_data: If given, this is read instead of the request's body.

	:raises hexc.HTTPBadRequest: If there is an error parsing/transforming the
			client request.
	"""
	value = input_data if input_data is not None else request.body
	ext_format = 'json'
	if (request.content_type or '').endswith( 'plist' ) \
		   or (request.content_type or '') == 'application/xml' \
		   or request.GET.get('format') == 'plist': # pragma: no cover
		ext_format = 'plist'

	__traceback_info__ = ext_format, value
	if ext_format != 'json': # pragma: no cover
		# We're officially dropping support for plist values.
		# primarily due to the lack of support for null values, and
		# unsure about encoding issues
		raise hexc.HTTPUnsupportedMediaType('XML no longer supported.')

	try:
		# We need all string values to be unicode objects. simplejson (the usual implementation
		# we get from anyjson) is different from the built-in json and returns strings
		# that can be represented as ascii as str objects if the input was a bytestring.
		# The only way to get it to return unicode is if the input is unicode, or
		# to use a hook to do so incrementally. The hook saves allocating the entire request body
		# as a unicode string in memory
		def _read_body_strings_unicode(pairs):
			return dict( ( (k, (unicode(v, request.charset) if isinstance(v, str) else v))
						   for k, v
						   in pairs) )

		value = simplejson.loads(value, object_pairs_hook=_read_body_strings_unicode)

		if not isinstance( value, expected_type ):
			raise TypeError( type(value) )

		# Depending on whether the simplejson C speedups are active, we can still
		# get back a non-unicode string if the object was a naked string. (If the python
		# version is used, it returns unicode; the C version returns str.)
		if isinstance( value, str ):
			value = unicode(value, 'utf-8') # we know it's simple ascii or it would have produced unicode

		return value
	except hexc.HTTPException: # pragma: no cover
		raise
	except Exception: # pragma: no cover
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

def handle_possible_validation_error( request, e ):
	if isinstance( e, zope.schema.interfaces.ValidationError ):
		if request is None:
			request = get_current_request()
		if request is None:
			_no_request_validation_error()
		else:
			handle_validation_error( request, e )
	elif isinstance( e, AssertionError): #pragma: no cover
		# Triggered a failed assertion on our side.
		# That's bad. We probably want this to come up as a 500
		# so we log it and deal with it
		raise
	elif isinstance( e, (ValueError,interface.Invalid,TypeError,KeyError)): # pragma: no cover
		# These are all 'validation' errors. Raise them as unprocessable entities
		# interface.Invalid, in particular, is the root class of zope.schema.ValidationError
		_no_request_validation_error()
	else:
		raise


def update_object_from_external_object( contentObject, externalValue, notify=True, request=None ):
	dataserver = component.queryUtility( nti_interfaces.IDataserver )
	try:
		__traceback_info__ = contentObject, externalValue
		return nti.externalization.internalization.update_from_external_object( contentObject, externalValue, context=dataserver, notify=notify )
	except Exception as e:
		handle_possible_validation_error( request, e )

def _no_request_validation_error():
	logger.exception( "Failed to update content object, bad input" )
	exc_info = sys.exc_info()
	raise hexc.HTTPUnprocessableEntity, exc_info[1], exc_info[2]

def handle_validation_error( request, validation_error ):
	"""
	Handles a :class:`zope.schema.interfaces.ValidationError` within the context
	of a Pyramid request by raising an :class:`pyramid.httpexceptions.HTTPUnprocessableEntity`
	error. Call from within the scope of a ``catch`` block.

	:param validation_error: The validation error being processed.

	"""
	__traceback_info__ = validation_error
	# Validation error may be many things, including invalid password by the policy (see above)
	# Some places try hard to set a good message, some don't.
	exc_info = sys.exc_info()
	field_name = None
	field = getattr( validation_error, 'field', None )
	msg = ''
	value = None
	if field:
		field_name = getattr( field, '__name__', field )
	if len(validation_error.args) == 3:
		# message, field, value
		field_name = field_name or validation_error.args[1]
		msg = validation_error.args[0]
		value = validation_error.args[2]

	if not field_name and isinstance( validation_error, pwd_interfaces.InvalidPassword ):
		field_name = 'password'

	if not field_name and isinstance( validation_error, zope.schema.interfaces.RequiredMissing ):
		field_name = validation_error.message

	if not value:
		value = getattr( validation_error, 'value', value )

	# z3c.password and similar (nti.dataserver.users._InvalidData) set this for internationalization
	# purposes
	if getattr(validation_error, 'i18n_message', None):
		msg = translate( validation_error.i18n_message )
	else:
		msg = validation_error.message or msg
		msg = translate(msg)

	raise_json_error( request,
					  hexc.HTTPUnprocessableEntity,
					  {'message': msg,
					   'field': field_name,
					   'code': validation_error.__class__.__name__,
					   'value': value },
					   exc_info[2] )
