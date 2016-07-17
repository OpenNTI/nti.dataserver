#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property

import unittest
from hashlib import sha512

from nose.tools import assert_raises

def _do_test_parse(AuthTicket, parse_ticket, BadTicket):

	time = 1234
	ip = b'0.0.0.0'
	secret = b'secret'
	user = b'foo@bar'
	
	tkt = AuthTicket( secret, user, ip, time=time )
	cookie_value = tkt.cookie_value()
	assert_that( parse_ticket( secret, cookie_value, ip ),
				 is_( (time, user, [''], '' ) ) )

	with assert_raises(BadTicket):
		cookie_value = cookie_value.replace( 'a', 'b' )
		parse_ticket( secret, cookie_value, ip )

def test_patch():
	import paste.auth.auth_tkt
	import nti.monkey.patch_paste_auth_tkt_sha512_on_import
	nti.monkey.patch_paste_auth_tkt_sha512_on_import.patch()

	assert_that( paste.auth.auth_tkt, has_property('md5', is_( sha512 ) ))

	assert_that( paste.auth.auth_tkt, has_property('DEFAULT_DIGEST', is_( sha512 ) ))
	
	_do_test_parse( paste.auth.auth_tkt.AuthTicket,
					paste.auth.auth_tkt.parse_ticket,
					paste.auth.auth_tkt.BadTicket )

try:
	import repoze.who._auth_tkt as is_repoze_21
	is_repoze_20 = False
except ImportError:
	is_repoze_21 = False
	is_repoze_20 = True

@unittest.skipIf(is_repoze_20, "Only needed under repoze.who 2.1" )
def test_patch_repoze21():
	import nti.monkey.patch_paste_auth_tkt_sha512_on_import
	nti.monkey.patch_paste_auth_tkt_sha512_on_import.patch()

	assert_that( is_repoze_21.md5, is_( sha512 ) )

	_do_test_parse( is_repoze_21.AuthTicket,
					is_repoze_21.parse_ticket,
					is_repoze_21.BadTicket )
