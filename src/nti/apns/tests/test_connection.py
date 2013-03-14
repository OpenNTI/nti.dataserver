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
from hamcrest import contains_string
from nose.tools import assert_raises

from zope import interface


from ..payload import APNSPayload
from ..connection import to_packet_bytes

def test_to_packet_bytes():
	payload = APNSPayload(alert='alert')
	deviceid = b'b' * 32

	# We refuse to send invalid payloads or device ids
	with assert_raises(interface.Invalid):
		to_packet_bytes( APNSPayload(), deviceid )

	with assert_raises(interface.Invalid):
		to_packet_bytes( payload, b'tooshort' )

	packet, _ = to_packet_bytes( payload, deviceid )
	assert_that( packet, is_( bytes ) )
	assert_that( packet[0], is_( b'\x01' ) )

	payload.userInfo = {'foo': 'bar'}
	packet, _ = to_packet_bytes( payload, deviceid )

	assert_that( packet, contains_string( b'foo' ) )
