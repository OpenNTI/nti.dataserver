#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import uuid

import stripe
from zope import component

from nti.externalization.externalization import toExternalObject

from .. import interfaces as stripe_interfaces

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_not, none, has_key, has_entry)

class TestZcml(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestZcml, cls).setUpClass()
		cls.api_key = stripe.api_key
		stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'

	@classmethod
	def tearDownClass(cls):
		super(TestZcml, cls).tearDownClass()
		stripe.api_key = cls.api_key

	def test_default_registrations(self):
		cap_name = 'NTI-TEST'
		sk = component.getUtility(stripe_interfaces.IStripeConnectKey, cap_name)
		assert_that(sk, is_not(none()))
		extobj = toExternalObject(sk)
		assert_that(extobj, is_not(has_key('PrivateKey')))
		assert_that(extobj, is_not(has_key('RefreshToken')))

	def test_coupon(self):
		code = str(uuid.uuid4())
		c = stripe.Coupon.create(percent_off=25, duration='once', id=code)
		ext = toExternalObject(c)
		assert_that(ext, is_not(none()))
		assert_that(ext, has_entry('ID', code))
		assert_that(ext, has_entry('Duration', 'once'))
		assert_that(ext, has_entry('PercentOff', 25))

