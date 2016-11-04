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

from nti.apns import interfaces

class TestInterfaces(unittest.TestCase):
	
	def test_feedback_event(self):
		event = interfaces.APNSDeviceFeedback(0, b'b' * 32)
		assert_that( event, validly_provides(interfaces.IDeviceFeedbackEvent) )
		assert_that( event, verifiably_provides(interfaces.IDeviceFeedbackEvent) )
		repr(event)
