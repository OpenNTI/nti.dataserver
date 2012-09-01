#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import pyramid.httpexceptions as _hexc
import sys

# Import some common things for the sake of static analysis
HTTPBadRequest = _hexc.HTTPBadRequest
HTTPConflict = _hexc.HTTPConflict
HTTPForbidden = _hexc.HTTPForbidden
HTTPUnsupportedMediaType = _hexc.HTTPUnsupportedMediaType
HTTPException = _hexc.HTTPException

# Dynamically import the rest
def _copy_pyramid_exceptions():
	frame = sys._getframe(1)
	for k,v in _hexc.__dict__.items():
		if isinstance( v, type) and issubclass(v,Exception) and v.__module__ == _hexc.__name__:
			frame.f_globals[k] = v
_copy_pyramid_exceptions()
del _copy_pyramid_exceptions
del sys


try:
	from pyramid.httpexceptions import HTTPUnprocessableEntity
	assert HTTPUnprocessableEntity.code == 422
except ImportError:
	class HTTPUnprocessableEntity(HTTPClientError):
		"""
		WebDAV extension for bad client input.

		The 422 (Unprocessable Entity) status code means the server
		understands the content type of the request entity (hence a
		415(Unsupported Media Type) status code is inappropriate), and the
		syntax of the request entity is correct (thus a 400 (Bad Request)
		status code is inappropriate) but was unable to process the contained
		instructions.  For example, this error condition may occur if an XML
		request body contains well-formed (i.e., syntactically correct), but
		semantically erroneous, XML instructions.

		http://tools.ietf.org/html/rfc4918#section-11.2
		"""
		code = 422
		title = "Unprocessable Entity"
		explanation = ('The client sent a well-formed but invalid request body.')

		def __str__( self ):
			# The super-class simply echoes back self.detail, which
			# if not a string, causes str() to raise TypeError
			return str(super(HTTPUnprocessableEntity,self).__str__())
