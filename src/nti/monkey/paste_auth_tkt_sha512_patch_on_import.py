#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapts :mod:`paste.auth.auth_tkt` to use SHA512 cookies instead of
MD5 cookies. This is a change inspired by Pyramid 1.4, which did
something similar in its own version of :class:`pyramid.authentication.AuthTkt`.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"


import functools

from hashlib import sha512
from hashlib import md5

import paste.auth.auth_tkt
import repoze.who.plugins.auth_tkt
from pyramid.authentication import parse_ticket as _pyramid_parse, BadTicket as _pyramid_BadTicket

@functools.wraps(_pyramid_parse)
def _parse_ticket( s, t, ip ):
	try:
		# The size of the digest changes from md5 to sha512. Pyramid
		# deals with this, paste does not
		return _pyramid_parse( s, t, ip, 'sha512' )
	except _pyramid_BadTicket as e:
		raise paste.auth.auth_tkt.BadTicket( e.message, e.expected )

def patch():
	try:
		if paste.auth.auth_tkt.md5 == md5:
			# We only have to change these here...
			paste.auth.auth_tkt.md5 = sha512
			paste.auth.auth_tkt.parse_ticket = _parse_ticket

			# ...because repoze imports the module
			assert repoze.who.plugins.auth_tkt.auth_tkt == paste.auth.auth_tkt
			assert 'parse_ticket' not in repoze.who.plugins.auth_tkt.__dict__
	except AttributeError:
		raise ImportError( "Paste does not use MD5 anymore. Incompatible change. FIXME" )

patch()
