#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )

import wsgiref.headers
import sys
import transaction
import pyramid.httpexceptions

# From http://www.w3.org/TR/cors/, 2011-10-18

SIMPLE_METHODS = ('GET', 'HEAD', 'POST')

SIMPLE_HEADERS = ('ACCEPT', 'ACCEPT-LANGUAGE',
				  'CONTENT-LANGUAGE', 'LAST-EVENT-ID')
SIMPLE_CONTENT_TYPES = ('application/x-www-form-urlencoded',
						'multipart/form-data', 'text/plain')
SIMPLE_RESPONSE_HEADERS = ('cache-control', 'content-language',
						   'content-type', 'expires',
						   'last-modified', 'pragma')

def is_simple_request_method( environ ):
	return environ['REQUEST_METHOD'] in SIMPLE_METHODS

def is_simple_header( name, value=None ):
	return name.upper() in SIMPLE_HEADERS \
		   or (name.upper() == 'CONTENT-TYPE' and value and value.lower() in SIMPLE_CONTENT_TYPES)

def is_simple_response_header( name ):
	return name and name.lower() in SIMPLE_RESPONSE_HEADERS

class CORSInjector(object):
	""" Inject CORS around any application. Should be wrapped around (before) authentication
	and before ErrorMiddleware. """
	def __init__( self, app ):
		self.captured = app

	def __call__( self, environ, start_request ):
		the_start_request = start_request
		# Support CORS
		# Our security policy here is extremely lax, support requests from
		# everywhere. We are strict about the methods we support.
		# When we care about security, we are "strongly encouraged" to
		# check the HOST header matches our actual host name.
		# HTTP_ORIGIN and -Allow-Origin are space separated lists that
		# are compared case-sensitively.
		if 'HTTP_ORIGIN' in environ:
			# For preflight requests, there MUST be a -Request-Method
			# provided. There also MUST be a -Request-Headers list.
			# The spec says that, if these two headers are not malformed,
			# they can effectively be ignored since they could be compared
			# to unbounded lists. We choose not to even check for them.
			local_start_request = the_start_request
			def f( status, headers, exc_info=None ):
				theHeaders = wsgiref.headers.Headers( headers )
				# For simple requests, we only need to set
				# -Allow-Origin, -Allow-Credentials, and -Expose-Headers.
				# If we fail, we destroy the browser's cache.
				# Since we support credentials, we cannot use the * wildcard origin.
				theHeaders['Access-Control-Allow-Origin'] = environ['HTTP_ORIGIN']
				theHeaders['Access-Control-Allow-Credentials'] = "true" # case-sensitive
				# We would need to add Access-Control-Expose-Headers to
				# expose non-simple response headers to the client, even on simple requests

				# All the other values are only needed for preflight requests,
				# which are OPTIONS
				if environ['REQUEST_METHOD'] == 'OPTIONS':
					theHeaders['Access-Control-Allow-Methods'] = 'POST, GET, PUT, DELETE, OPTIONS'
					theHeaders['Access-Control-Max-Age'] = "1728000" # 20 days
					theHeaders['Access-Control-Allow-Headers'] = 'Slug, X-Requested-With, Authorization, If-Modified-Since, Content-Type, Origin, Accept, Cookie'
					theHeaders['Access-Control-Expose-Headers'] = 'Location, Warning'

				return local_start_request( status, headers, exc_info )
			the_start_request = f
		result = None
		try:
			environ.setdefault( 'paste.expected_exceptions', [] ).append( transaction.interfaces.DoomedTransaction )
			environ.setdefault( 'paste.expected_exceptions', [] ).append( pyramid.httpexceptions.HTTPException )
			result = self.captured( environ, the_start_request )
		except transaction.interfaces.DoomedTransaction:
			# No biggie, let the real response go out.
			pass
		except pyramid.httpexceptions.HTTPException:
			raise
		except Exception as e:
			# The vast majority of these we expect to be caught by paste.
			# We don't do anything fancy, just log and continue
			logger.exception( "Failed to handle request" )
			result = ('Failed to handle request ' + str(e),)
			start_request( '500 Internal Server Error', [('Content-Type', 'text/plain')], sys.exc_info() )

		return result

def cors_filter_factory( app, global_conf ):
	return CORSInjector(app)
