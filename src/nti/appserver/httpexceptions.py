#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

import pyramid.httpexceptions as _hexc
import sys

# Import some common things for the sake of static analysis
HTTPBadRequest = _hexc.HTTPBadRequest
HTTPConflict = _hexc.HTTPConflict
HTTPForbidden = _hexc.HTTPForbidden
HTTPUnsupportedMediaType = _hexc.HTTPUnsupportedMediaType
HTTPException = _hexc.HTTPException
HTTPNotFound = _hexc.HTTPNotFound
HTTPFound = _hexc.HTTPFound
HTTPNoContent = _hexc.HTTPNoContent
HTTPMethodNotAllowed = _hexc.HTTPMethodNotAllowed
HTTPSeeOther = _hexc.HTTPSeeOther

# Dynamically import the rest
def _copy_pyramid_exceptions():
	frame = sys._getframe(1)
	for k,v in _hexc.__dict__.items():
		if isinstance( v, type) and issubclass(v,Exception) and v.__module__ == _hexc.__name__:
			frame.f_globals[k] = v
_copy_pyramid_exceptions()



_HTTPUnprocessableEntity = _hexc.HTTPUnprocessableEntity

# Our class has much better docs and deals better with representations
# Subclass before we swizzle in case anyone has directly imported that class,
# so when we throw we will still be caught
class HTTPUnprocessableEntity(_HTTPUnprocessableEntity):
	"""
	WebDAV extension for bad client input.

	The 422 (Unprocessable Entity) status code means the server
	understands the content type of the request entity (hence a
	415 (Unsupported Media Type) status code is inappropriate), and the
	syntax of the request entity is correct (thus a 400 (Bad Request)
	status code is inappropriate) but was unable to process the contained
	instructions.  For example, this error condition may occur if an XML
	request body contains well-formed (i.e., syntactically correct), but
	semantically erroneous, XML instructions.

	http://tools.ietf.org/html/rfc4918#section-11.2

	code: 422, title: Unprocessable Entity
	"""

	def __str__( self ):
		# The super-class simply echoes back self.detail, which
		# if not a string, causes str() to raise TypeError
		return str(super(HTTPUnprocessableEntity,self).__str__())

_hexc.HTTPUnprocessableEntity = HTTPUnprocessableEntity

del _copy_pyramid_exceptions
del sys
del _hexc
