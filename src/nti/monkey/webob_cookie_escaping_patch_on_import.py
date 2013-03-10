#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Versions of :mod:`webob.cookie` up through at least 1.2.3 are overly
aggressive when it comes to escaping the values of the Set-Cookie
header.

According to `RFC 6265 <http://tools.ietf.org/html/rfc6265#section-4.1.1>`, only a few values
have to be escaped: control characters, double quote, comma, semicolon, and backslash. Notably, the at-sign, @, is
allowed. However, webob leaves this on its list.

Importing this module (and calling patch) adjusts the webob cookie functions to not
escape these values.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from webob import cookies as _cookies
from webob.cookies import _quote # Raise ImportError if the internals have changed


# First, see if it needs to be escaped
if _quote( b'foo@bar' ) != 'foo@bar':
	# Again, raise ImportError if the internals have changed
	try:
		getattr( _cookies, '_no_escape_special_chars' )
		getattr( _cookies, '_no_escape_chars' )
		getattr( _cookies, '_no_escape_bytes' )
	except AttributeError:
		raise ImportError("WebOb internals have changed")

	_cookies._no_escape_special_chars = _cookies._no_escape_special_chars + b'@'
	_cookies._no_escape_chars = _cookies._no_escape_chars + b'@'
	_cookies._no_escape_bytes = _cookies._no_escape_bytes + b'@'

	# Safe to leave the maps alone

	try:
		assert _quote( b'foo@bar' ) == 'foo@bar'
	except AssertionError:
		raise ImportError( "Unable to patch WebOb correctly" )

def patch():
	pass

patch()
