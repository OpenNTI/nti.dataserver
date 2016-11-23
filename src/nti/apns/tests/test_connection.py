#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string
from nose.tools import assert_raises

import unittest

from zope import interface

from nti.apns.connection import to_packet_bytes

from nti.apns.payload import APNSPayload

class TestConnection(unittest.TestCase):

	def test_to_packet_bytes(self):
		payload = APNSPayload(alert='alert')
		# Real-world example of a token
		deviceid = b'\x90\xc7\xb1\xd5\nA\xc3\xf5\x81\xb4h|\xe1!:\xc7\xd6k\xeaFe\xf4\x04fq\xb3\x08\x04\x17^ ^'

		# We refuse to send invalid payloads or device ids
		with assert_raises(interface.Invalid):
			to_packet_bytes(APNSPayload(), deviceid)

		with assert_raises(interface.Invalid) as ex:
			to_packet_bytes(payload, b'tooshort')

		assert_that(ex.exception, has_property('field', has_property('__name__', 'deviceId')))

		packet, _ = to_packet_bytes(payload, deviceid)
		assert_that(packet, is_(bytes))
		assert_that(packet[0], is_(b'\x01'))

		payload.userInfo = {'foo': 'bar'}
		packet, _ = to_packet_bytes(payload, deviceid)

		assert_that(packet, contains_string(b'foo'))
