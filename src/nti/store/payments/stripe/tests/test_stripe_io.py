#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import time
import uuid
import stripe
import unittest
from datetime import date

from .. import stripe_io

from hamcrest import (assert_that, is_, is_not, has_length, greater_than_or_equal_to)
			
@unittest.SkipTest
class TestStripeIO(unittest.TestCase):
	
	@classmethod
	def setUpClass(cls):
		super(TestStripeIO,cls).setUpClass()
		cls.api_key = stripe.api_key
		stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'
		
	@classmethod
	def tearDownClass(cls):
		super(TestStripeIO,cls).tearDownClass()
		stripe.api_key = cls.api_key
	
	def test_create_update_delete_customer(self):
		code =  str(uuid.uuid4()).split('-')[0]
		username = u'u' + code
		email = username + '@nextthought.com'
		description = 'test user ' +  code
		
		sio = stripe_io.StripeIO()
		customer = sio.create_stripe_customer(email, description)
		assert_that(customer, is_not(None))
		
		customer = sio.get_stripe_customer(customer.id)
		assert_that(customer, is_not(None))
		
		r = sio.update_stripe_customer(customer, 'xyz@nt.com')
		assert_that(r, is_(True))
		assert_that(customer.email, is_('xyz@nt.com'))
		
		r = sio.delete_stripe_customer(customer.id, customer=customer)
		assert_that(r, is_(True))
		
	def test_create_token_and_charge(self):
		sio = stripe_io.StripeIO()
		t = sio.create_stripe_token(number="5105105105105100", 
									exp_month="11",
									exp_year="30",
									cvc="542",
									address="3001 Oak Tree #D16",
									city="Norman",
									zip = "73072",
									state="OK",
									country="USA")
		assert_that(t, is_not(None))
		
		t = sio.get_stripe_token(t.id)
		assert_that(t, is_not(None))
		assert_that(t.used, is_(False))

		c = sio.create_stripe_charge(amount=100, card=t.id, description="my charge")
		assert_that(c, is_not(None))
		
		sio.get_stripe_charge(c.id)
		assert_that(c, is_not(None))
		
		start_time = time.mktime(date.today().timetuple())
		charges = list(sio.get_stripe_charges(start_time=start_time, count=50))
		assert_that(charges, has_length(greater_than_or_equal_to(1)))
		
	def test_invalid_token(self):
		sio = stripe_io.StripeIO()
		t = sio.get_stripe_token('tok_unknown')
		assert_that(t, is_(None))
		
	def test_invalid_charge(self):
		sio = stripe_io.StripeIO()
		c = sio.get_stripe_charge('c_unknown')
		assert_that(c, is_(None))
		
	def test_invalid_customer(self):
		sio = stripe_io.StripeIO()
		c = sio.get_stripe_customer('cus_unknown')
		assert_that(c, is_(None))
		
	def test_coupon(self):
		code =  str(uuid.uuid4()).split('-')[0]
		c = stripe.Coupon.create(percent_off=25,duration='once', id=code)
		try:
			sio = stripe_io.StripeIO()
			coupon = sio.get_stripe_coupon(code)
			assert_that(coupon, is_not(None))
		finally:
			c.delete()
	
	def test_invalid_coupon(self):
		code =  'notknown'
		sio = stripe_io.StripeIO()
		coupon = sio.get_stripe_coupon(code)
		assert_that(coupon, is_(None))
