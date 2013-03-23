#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapts :mod:`paste.auth.auth_tkt` to use SHA512 cookies instead of
MD5 cookies. This is a change inspired by Pyramid 1.4, which did
something similar in its own version of :class:`pyramid.authentication.AuthTkt`.

The :mod:`repoze.who` system relies on Paste in 2.0, but no longer
does in 2.1, so this also performs cleanup work in that module.

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
		raise paste.auth.auth_tkt.BadTicket( e.args[0], e.expected )

def patch():
	def _patch( mod ):
		if mod.md5 == md5:
			mod.md5 = sha512
			mod.parse_ticket = _parse_ticket

	try:
		from repoze.who import _auth_tkt as who_auth_tkt
		# Match the exceptions
		paste.auth.auth_tkt.BadTicket = who_auth_tkt.BadTicket
		_patch( who_auth_tkt )
	except ImportError:
		who_auth_tkt = None

	try:
		# We only have to change these here...
		_patch( paste.auth.auth_tkt )
		# ...because repoze imports the module (in 2.0)
		if who_auth_tkt is None:
			assert repoze.who.plugins.auth_tkt.auth_tkt == paste.auth.auth_tkt
		else: # 2.1
			assert repoze.who.plugins.auth_tkt.auth_tkt == who_auth_tkt

		assert 'parse_ticket' not in repoze.who.plugins.auth_tkt.__dict__
	except AttributeError:
		raise ImportError( "Paste does not use MD5 anymore. Incompatible change. FIXME" )

patch()
