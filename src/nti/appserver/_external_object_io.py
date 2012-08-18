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


from zope import component
from zope import interface

from nti.appserver import httpexceptions as hexc

import simplejson

from nti.dataserver import interfaces as nti_interfaces
import nti.externalization.internalization



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

def update_object_from_external_object( contentObject, externalValue, notify=True ):
	dataserver = component.queryUtility( nti_interfaces.IDataserver )
	try:
		__traceback_info__ = contentObject, externalValue
		return nti.externalization.internalization.update_from_external_object( contentObject, externalValue, context=dataserver, notify=notify )
	except (ValueError,AssertionError,interface.Invalid,TypeError,KeyError): # pragma: no cover
		# These are all 'validation' errors. Raise them as unprocessable entities
		# interface.Invalid, in particular, is the root class of zope.schema.ValidationError
		logger.exception( "Failed to update content object, bad input" )
		exc_info = sys.exc_info()
		raise hexc.HTTPUnprocessableEntity, exc_info[1], exc_info[2]
