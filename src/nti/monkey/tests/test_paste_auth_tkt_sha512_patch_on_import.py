#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

from nose.tools import assert_raises

import nti.tests

from hashlib import sha512

def test_patch():
	import paste.auth.auth_tkt
	import nti.monkey.paste_auth_tkt_sha512_patch_on_import
	nti.monkey.paste_auth_tkt_sha512_patch_on_import.patch()

	assert_that( paste.auth.auth_tkt.md5, is_( sha512 ) )

	from paste.auth.auth_tkt import AuthTicket, parse_ticket

	secret = b'secret'
	time = 1234
	user = b'foo@bar'
	ip = b'0.0.0.0'

	tkt = AuthTicket( secret, user, ip, time=time )
	cookie_value = tkt.cookie_value()
	assert_that( parse_ticket( secret, cookie_value, ip ),
				 is_( (time, user, [''], '' ) ) )

	with assert_raises(paste.auth.auth_tkt.BadTicket):
		cookie_value = cookie_value.replace( 'a', 'b' )
		parse_ticket( secret, cookie_value, ip )
