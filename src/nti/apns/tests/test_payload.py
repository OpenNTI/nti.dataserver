#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

import unittest

from nti.apns.interfaces import INotificationPayload

from nti.apns.payload import APNSPayload

class TestPayload(unittest.TestCase):

	def test_payload_provides(self):

		payload = APNSPayload()
		assert_that(payload, verifiably_provides(INotificationPayload))

		payload.alert = "alert"
		assert_that(payload, validly_provides(INotificationPayload))
