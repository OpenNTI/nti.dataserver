#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An outer layer middleware designed to work with `CORS`_. Also integrates with
Paste to set up expected exceptions. The definitions here were lifted from the
`CORS`_ spec on 2011-10-18.

$Id$

.. _CORS: http://www.w3.org/TR/cors/
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import wsgiref.headers
import functools

# Exceptions we will ignore for middleware purposes
import greenlet

#: The exceptions in this list will be considered expected
#: and not create error reports from Paste. Instead, Paste
#: will raise them, and they will be caught here. Paste will
#: catch everything else.
EXPECTED_EXCEPTIONS = (greenlet.GreenletExit, # During restarts this can be generated
					   # Most commonly (almost only) seen buffering request bodies. May have some false negatives, though.
					   # Also seen when a umysqldb connection fails; hard to determine when that can be retryable; this
					   # is one of those false-negatives
					   IOError,
					   )
# Previously this contained:
# transaction.interfaces.DoomedTransaction, # This should never get here with the transaction middleware in place
# pyramid.httpexceptions.HTTPException, # Pyramid is beneath us, so this should never get here either

SIMPLE_METHODS = (b'GET', b'HEAD', b'POST') #: HTTP methods that `CORS`_ defines as "simple"

SIMPLE_HEADERS = (b'ACCEPT', b'ACCEPT-LANGUAGE',
				  b'CONTENT-LANGUAGE', b'LAST-EVENT-ID') #: HTTP request headers that `CORS`_ defines as "simple"
SIMPLE_CONTENT_TYPES = (b'application/x-www-form-urlencoded',
						b'multipart/form-data', b'text/plain') #: HTTP content types that `CORS`_ defines as "simple"
SIMPLE_RESPONSE_HEADERS = (b'cache-control', b'content-language',
						   b'content-type', b'expires',
						   b'last-modified', b'pragma') #: HTTP response headers that `CORS`_ defines as simple

def is_simple_request_method( environ ):
	"Checks to see if the environment represents a simple `CORS`_ request"
	return environ['REQUEST_METHOD'] in SIMPLE_METHODS

def is_simple_header( name, value=None ):
	"Checks to see if the name represents a simple `CORS`_ request header"
	return name.upper() in SIMPLE_HEADERS \
		   or (name.upper() == 'CONTENT-TYPE' and value and value.lower() in SIMPLE_CONTENT_TYPES)

def is_simple_response_header( name ):
	"Checks to see if the name represents a simple `CORS`_ response header"
	return name and name.lower() in SIMPLE_RESPONSE_HEADERS

class CORSInjector(object):
	""" Inject CORS around any application. Should be wrapped around (before) authentication
	and before :class:`~paste.exceptions.errormiddleware.ErrorMiddleware`.
	"""

	__slots__ = ('_app',)

	def __init__( self, app ):
		self._app = app

	def __call__( self, environ, start_response ):
		# Support CORS
		if 'HTTP_ORIGIN' in environ:
			start_response = self._CORSInjectingStartResponse( environ, start_response )

		result = None
		environ.setdefault( b'paste.expected_exceptions', [] ).extend( EXPECTED_EXCEPTIONS )
		try:
			result = self._app( environ, start_response )
		except EXPECTED_EXCEPTIONS as e:
			# We don't do anything fancy, just log and continue
			logger.exception( "Failed to handle request" )
			result = (b'Failed to handle request ' + str(e),)
			start_response( b'500 Internal Server Error', [(b'Content-Type', b'text/plain')], sys.exc_info() )

		# Everything else we allow to propagate. This might kill the gunicorn worker and cause it to respawn
		# If so, it will be printed on stderr and captured by supervisor

		return result

	class _CORSInjectingStartResponse(object):
		"""
		A callable object that wraps a start_response callable to inject
		CORS headers.

		Our security policy here is extremely lax, support requests from
		everywhere. We are strict about the methods we support.

		When we care about security, we are "strongly encouraged" to
		check the HOST header matches our actual host name.
		HTTP_ORIGIN and -Allow-Origin are space separated lists that
		are compared case-sensitively.
		"""
		__slots__ = ('_start_response', '_environ')

		def __init__( self, environ, start_response ):
			self._start_response = start_response
			self._environ = environ

		def __call__( self, status, headers, exc_info=None ):
			# For preflight requests, there MUST be a -Request-Method
			# provided. There also MUST be a -Request-Headers list.
			# The spec says that, if these two headers are not malformed,
			# they can effectively be ignored since they could be compared
			# to unbounded lists. We choose not to even check for them.

			environ = self._environ
			theHeaders = wsgiref.headers.Headers( headers )
			# For simple requests, we only need to set
			# -Allow-Origin, -Allow-Credentials, and -Expose-Headers.
			# If we fail, we destroy the browser's cache.
			# Since we support credentials, we cannot use the * wildcard origin.
			theHeaders[b'Access-Control-Allow-Origin'] = environ['HTTP_ORIGIN']
			theHeaders[b'Access-Control-Allow-Credentials'] = b"true" # case-sensitive
			# We would need to add Access-Control-Expose-Headers to
			# expose non-simple response headers to the client, even on simple requests

			# All the other values are only needed for preflight requests,
			# which are OPTIONS
			if environ['REQUEST_METHOD'] == b'OPTIONS':
				theHeaders[b'Access-Control-Allow-Methods'] = b'POST, GET, PUT, DELETE, OPTIONS'
				theHeaders[b'Access-Control-Max-Age'] = b"1728000" # 20 days
				# TODO: Should we inspect the Access-Control-Request-Headers at all?
				theHeaders[b'Access-Control-Allow-Headers'] = b'Pragma, Slug, X-Requested-With, Authorization, If-Modified-Since, Content-Type, Origin, Accept, Cookie, Accept-Encoding, Cache-Control'
				theHeaders[b'Access-Control-Expose-Headers'] = b'Location, Warning'

			return self._start_response( status, headers, exc_info )


def cors_filter_factory( app, global_conf=None ):
	"Paste filter factory to include :class:`CORSInjector`"
	return CORSInjector(app)

class CORSOptionHandler(object):
	"""
	Handle OPTIONS requests by simply swallowing them and not letting
	them come through to the following app.

	This is useful with the :func:`cors_filter_factory` and should be
	beneath it. Only use this if the rest of the pipeline doesn't
	handle OPTIONS requests.
	"""

	__slots__ = ('_app',)

	def __init__( self, app ):
		self._app = app

	def __call__( self, environ, start_response ):
		# TODO: The OPTIONS method should be better implemented. We are
		# swallowing all OPTION requests at this level.

		if environ['REQUEST_METHOD'] == b'OPTIONS':
			start_response( b'200 OK', [(b'Content-Type', b'text/plain')] )
			return (b'',)

		return self._app( environ, start_response )


def cors_option_filter_factory( app, global_conf=None ):
	"Paste filter factory to include :class:`CORSOptionHandler`"
	return CORSOptionHandler( app )
