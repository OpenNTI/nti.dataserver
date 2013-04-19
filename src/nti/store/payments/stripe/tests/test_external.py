#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import uuid
import stripe

from nti.externalization.externalization import toExternalObject

from .. import StripePurchaseError

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_not, none, has_entry)

class TestExternal(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestExternal, cls).setUpClass()
		cls.api_key = stripe.api_key
		stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'

	@classmethod
	def tearDownClass(cls):
		super(TestExternal, cls).tearDownClass()
		stripe.api_key = cls.api_key

	def test_external_stripe_coupon(self):
		code = str(uuid.uuid4())
		c = stripe.Coupon.create(percent_off=25, duration='once', id=code)
		ext = toExternalObject(c)
		assert_that(ext, is_not(none()))
		assert_that(ext, has_entry('ID', code))
		assert_that(ext, has_entry('Duration', 'once'))
		assert_that(ext, has_entry('PercentOff', 25))

	def test_external_purchase_errorn(self):
		spe = StripePurchaseError(Type=u"Error", Message=u"My message", Code=u"My code", Param=u"My param")
		ext = toExternalObject(spe)
		assert_that(ext, is_not(none()))
		assert_that(ext, has_entry('Type', 'Error'))
		assert_that(ext, has_entry('Message', 'My message'))
		assert_that(ext, has_entry('Code', "My code"))
		assert_that(ext, has_entry('Param', "My param"))


