#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time
import uuid
import stripe
import unittest

from zope import component
from zope.annotation import IAnnotations

from nti.dataserver.users import User

from nti.store.payments.stripe import stripe_purchase
from nti.store.payments.stripe import interfaces as stripe_interfaces

from nti.store import purchase_history
from nti.store import interfaces as store_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from zope.component import eventtesting
from hamcrest import (assert_that, is_, is_not, has_length, has_key, none)

TEST_WITH_STRIPE = True

def _create_user(username='nt@nti.com', password='temp001', **kwargs):
	ds = mock_dataserver.current_mock_ds
	ext_value = {'external_value':kwargs}
	usr = User.create_user(ds, username=username, password=password, **ext_value)
	return usr

def _create_random_user():
	code = str(uuid.uuid4()).split('-')[0]
	username = u'u' + code
	email = username + '@nextthought.com'
	desc = 'test user ' + code
	user = _create_user(username=username, email=email, description=desc)
	return user

def _create_purchase_attempt(item, processor, quantity=None, description=None, coupon=None):
	pi = stripe_purchase.create_stripe_purchase_item(item, 1)
	po = stripe_purchase.create_stripe_purchase_order(pi, quantity=quantity, coupon=coupon)
	pa = purchase_history.create_purchase_attempt(po, processor=processor, description=description)
	return pa

def _create_and_register_purchase_attempt(username, item, quantity=None, processor=None, coupon=None,
										  description="my charge"):
	pa = _create_purchase_attempt(item, quantity=quantity, processor=processor, coupon=coupon, description=description)
	purchase_id = purchase_history.register_purchase_attempt(pa, username)
	return purchase_id

def create_purchase(self, item=None, amount=100, coupon=None, manager=None):
	ds = self.ds
	manager = manager or self.manager
	item = item or self.book_id

	with mock_dataserver.mock_db_trans(ds):
		user = _create_random_user()
		username = user.username

	with mock_dataserver.mock_db_trans(ds):

		purchase_id = _create_and_register_purchase_attempt(username, item=item, processor=manager.name, coupon=coupon)
		assert_that(purchase_id, is_not(none()))


	tid = manager.create_card_token(number="5105105105105100",
										 exp_month="11",
										 exp_year="30",
										 cvc="542",
										 address="3001 Oak Tree #D16",
										 city="Norman",
										 zip="73072",
										 state="OK",
										 country="USA")

	cid = manager.process_purchase(username=username, token=tid,
								   purchase_id=purchase_id, expected_amount=amount)

	assert_that(tid, is_not(none()))
	assert_that(cid, is_not(none()))

	return username, purchase_id, tid, cid

class TestStripeProcessor(ConfiguringTestBase):

	book_id = 'xyz-book'

	@classmethod
	def setUpClass(cls):
		super(TestStripeProcessor, cls).setUpClass()
		cls.api_key = stripe.api_key
		stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'

	@classmethod
	def tearDownClass(cls):
		super(TestStripeProcessor, cls).tearDownClass()
		stripe.api_key = cls.api_key

	def setUp(self):
		super(TestStripeProcessor, self).setUp()
		self.manager = component.getUtility(store_interfaces.IPaymentProcessor, name='stripe')


	@WithMockDSTrans
	def test_create_token_and_charge(self):
		t = self.manager.create_card_token(number="5105105105105100",
											exp_month="11",
											exp_year="30",
											cvc="542",
											address="3001 Oak Tree #D16",
											city="Norman",
											zip="73072",
											state="OK",
											country="USA")
		assert_that(t, is_not(none()))

		c = self.manager.create_charge(100, card=t, description="my charge")
		assert_that(c, is_not(none()))


	create_purchase = create_purchase

	@WithMockDSTrans
	def test_price_purchase_no_coupon(self):
		ds = self.ds

		with mock_dataserver.mock_db_trans(ds):
			item = self.book_id
			user = _create_random_user()
			username = user.username
			purchase_id = _create_and_register_purchase_attempt(username, item=item, quantity=2, processor=self.manager.name)

		result = self.manager.price_purchase(username=username, purchase_id=purchase_id)
		assert_that(result, is_not(none()))
		assert_that(result.TotalPurchaseFee, is_(0))
		assert_that(result.TotalPurchasePrice, is_(200))
		assert_that(result.TotalNonDiscountedPrice, is_(200))

	@unittest.skipUnless(TEST_WITH_STRIPE, '')
	@WithMockDSTrans
	def test_process_payment(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			username, purchase_id, _, _ = self.create_purchase()

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.State, is_(store_interfaces.PA_STATE_SUCCESS))

		assert_that(eventtesting.getEvents(stripe_interfaces.IStripeCustomerCreated), has_length(1))

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptStarted), has_length(1))

		assert_that(eventtesting.getEvents(stripe_interfaces.IRegisterStripeToken), has_length(1))
		assert_that(eventtesting.getEvents(stripe_interfaces.IRegisterStripeCharge), has_length(1))

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptSuccessful), has_length(1))

		with mock_dataserver.mock_db_trans(ds):
			user = User.get_user(username)
			su = stripe_interfaces.IStripeCustomer(user)
			akey = "%s.%s" % (su.__class__.__module__, su.__class__.__name__)
			self.manager.delete_customer(username)
		assert_that(eventtesting.getEvents(stripe_interfaces.IStripeCustomerDeleted), has_length(1))

		with mock_dataserver.mock_db_trans(ds):
			user = User.get_user(username)
			assert_that(IAnnotations(user), is_not(has_key(akey)))

	@unittest.skipUnless(TEST_WITH_STRIPE, '')
	@WithMockDSTrans
	def test_process_payment_coupon(self):

		code = str(uuid.uuid4()).split('-')[0]
		c = stripe.Coupon.create(percent_off=50, duration='once', id=code)

		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			username, purchase_id, _, _ = self.create_purchase(amount=50, coupon=c.id)

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.State, is_(store_interfaces.PA_STATE_SUCCESS))

		assert_that(eventtesting.getEvents(stripe_interfaces.IStripeCustomerCreated), has_length(1))

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptStarted), has_length(1))

		assert_that(eventtesting.getEvents(stripe_interfaces.IRegisterStripeToken), has_length(1))
		assert_that(eventtesting.getEvents(stripe_interfaces.IRegisterStripeCharge), has_length(1))

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptSuccessful), has_length(1))

		c.delete()

	@WithMockDSTrans
	def test_fail_payment_invalid_token(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = _create_random_user()
			username = user.username

		with mock_dataserver.mock_db_trans(ds):
			item = self.book_id
			purchase_id = _create_and_register_purchase_attempt(username, item=item, processor=self.manager.name)

		with self.assertRaises(Exception):
			self.manager.process_purchase(username=username, token="++invalidtoken++",
										  purchase_id=purchase_id, expected_amount=100.0)

		assert_that(eventtesting.getEvents(stripe_interfaces.IStripeCustomerCreated), has_length(1))
		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptStarted), has_length(1))
		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptFailed), has_length(1))

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.State, is_(store_interfaces.PA_STATE_FAILED))

	@WithMockDSTrans
	def test_fail_payment_invalid_expected_amount(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = _create_random_user()
			username = user.username

		with mock_dataserver.mock_db_trans(ds):
			item = self.book_id
			purchase_id = _create_and_register_purchase_attempt(username, item=item, processor=self.manager.name)

		with self.assertRaises(Exception):
			self.manager.process_purchase(username=username, token="++valid++",
										  purchase_id=purchase_id, expected_amount=20000.0)

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptFailed), has_length(1))

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.State, is_(store_interfaces.PA_STATE_FAILED))

	@unittest.skipUnless(TEST_WITH_STRIPE, '')
	@WithMockDSTrans
	def test_sync_pending_purchase(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			username, purchase_id, tid, cid = self.create_purchase()

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchaseAttempt(pa)
			assert_that(sp.token_id, is_(tid))
			assert_that(sp.charge_id, is_(cid))

			# change state for synching
			pa.State = store_interfaces.PA_STATE_STARTED

		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username, api_key=stripe.api_key)
			assert_that(charge, is_not(None))

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.State, is_(store_interfaces.PA_STATE_SUCCESS))

	@unittest.skipUnless(TEST_WITH_STRIPE, '')
	@WithMockDSTrans
	def test_sync_invalid_charge_id(self):
		ds = self.ds
		username, purchase_id, _, _ = self.create_purchase()

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchaseAttempt(pa)
			sp.charge_id = 'invalid'

		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username)
			assert_that(charge, is_(None))

	@unittest.skipUnless(TEST_WITH_STRIPE, '')
	@WithMockDSTrans
	def test_sync_invalid_missing_charge_id(self):
		ds = self.ds
		username, purchase_id, _, _ = self.create_purchase()

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchaseAttempt(pa)
			sp.charge_id = None

		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username, api_key=stripe.api_key)
			assert_that(charge, is_not(None))

	@unittest.skipUnless(TEST_WITH_STRIPE, '')
	@WithMockDSTrans
	def test_sync_with_tokens(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = _create_random_user()
			username = user.username

		with mock_dataserver.mock_db_trans(ds):
			item = self.book_id
			purchase_id = _create_and_register_purchase_attempt(username, item=item, processor=self.manager.name)

		# missing token
		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username)
			assert_that(charge, is_(None))

		tid = self.manager.create_card_token(number="5105105105105100",
										 	 exp_month="11",
										 	 exp_year="30",
										 	 cvc="542",
										 	 address="3001 Oak Tree #D16",
										 	 city="Norman",
										 	 zip="73072",
										 	 state="OK",
										 	 country="USA")

		# unused token
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchaseAttempt(pa)
			sp.TokenID = tid

		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username)
			assert_that(charge, is_(None))

	def test_validate_coupon(self):
		class Coupon(object):
			duration = 'forever'
			redeem_by = None
			max_redemptions = None
			duration_in_months = None

		c = Coupon()
		c.duration = 'forever'
		assert_that(self.manager.validate_coupon(c), is_(True))

		c.duration = 'once'
		assert_that(self.manager.validate_coupon(c), is_(True))
		c.redeem_by = time.time() + 100000
		assert_that(self.manager.validate_coupon(c), is_(True))
		c.redeem_by = time.time() - 100000
		assert_that(self.manager.validate_coupon(c), is_(False))

		c.duration = 'repeating'
		assert_that(self.manager.validate_coupon(c), is_(False))
		c.redeem_by = time.time() + 100000
		assert_that(self.manager.validate_coupon(c), is_(True))
		c.redeem_by = None
		c.max_redemptions = 0
		assert_that(self.manager.validate_coupon(c), is_(False))
		c.max_redemptions = 1
		assert_that(self.manager.validate_coupon(c), is_(True))
		c.max_redemptions = None
		c.duration_in_months = 0
		assert_that(self.manager.validate_coupon(c), is_(False))
		c.duration_in_months = 10
		assert_that(self.manager.validate_coupon(c), is_(True))

	def test_apply_coupon(self):
		amount = 1000
		class Coupon(object):
			amount_off = None
			percent_off = None

		c = Coupon()
		c.percent_off = 0.10
		amt = self.manager.apply_coupon(amount, c)
		assert_that(amt, is_(900))

		c = Coupon()
		c.percent_off = 20.0
		amt = self.manager.apply_coupon(amount, c)
		assert_that(amt, is_(800))

		c = Coupon()
		c.amount_off = 2000
		amt = self.manager.apply_coupon(amount, c)
		assert_that(amt, is_(980))
