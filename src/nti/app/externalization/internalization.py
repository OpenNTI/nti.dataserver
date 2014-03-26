#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support functions for reading objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from . import MessageFactory as _

logger = __import__('logging').getLogger(__name__)

import collections
import sys
import simplejson
from webob.compat import url_unquote

from zope import component

from pyramid import httpexceptions as hexc

from nti.dataserver import interfaces as nti_interfaces
from nti.mimetype.mimetype import nti_mimetype_class
from nti.externalization.internalization import update_from_external_object
from nti.externalization.internalization import find_factory_for

from .error import handle_possible_validation_error

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
		result = find_factory_for( externalValue )
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

# Native string types for these values to avoid encoding
# problems
_mt_encoded = str('application/x-www-form-urlencoded')
_equal = str('=')

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
	content_type = getattr(request, 'content_type', '')
	if (content_type.endswith( 'plist' )
		or content_type == 'application/xml'
		or request.GET.get('format') == 'plist'): # pragma: no cover
		ext_format = 'plist'

	if content_type.startswith(_mt_encoded) and _equal in value:
		# Hmm, uh-oh. How did this happen?
		# We've seen this come in from the browser, but we're expecting JSON;
		# the standard WebOb way to decode it doesn't work in these cases.
		# Try it here
		value = url_unquote(value)
		if value.endswith(_equal):
			value = value[:-1]

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
		# as a unicode string in memory and is marginally faster in some cases. However,
		# the hooks gets to be complicated if it correctly catches everything (inside arrays,
		# for example; the function below misses them) so decoding to unicode up front
		# is simpler
		#def _read_body_strings_unicode(pairs):
		#	return dict( ( (k, (unicode(v, request.charset) if isinstance(v, str) else v))
		#				   for k, v
		#				   in pairs) )
		try:
			value = simplejson.loads(unicode(value, request.charset))
		except UnicodeError:
			# Try the most common web encoding
			value = simplejson.loads(unicode(value, 'iso-8859-1'))

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
		ex = hexc.HTTPBadRequest( _("Failed to parse/transform input"))
		raise ex, None, tb


def update_object_from_external_object( contentObject, externalValue, notify=True, request=None ):
	dataserver = component.queryUtility( nti_interfaces.IDataserver )
	try:
		__traceback_info__ = contentObject, externalValue
		return update_from_external_object( contentObject, externalValue, context=dataserver, notify=notify )
	except Exception as e:
		handle_possible_validation_error( request, e )
