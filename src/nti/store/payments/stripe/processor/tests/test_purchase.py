#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import assert_that

import uuid
import stripe
import unittest

from zope.annotation import IAnnotations

from nti.dataserver.users import User

from nti.store.payments.stripe import interfaces as stripe_interfaces

from nti.store import purchase_history
from nti.store import interfaces as store_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from zope.component import eventtesting

from ..purchase import PurchaseProcessor

from . import create_purchase
from . import TEST_WITH_STRIPE
from . import create_random_user
from . import ConfiguringTestBase
from . import TestBaseProcessorMixin
from . import create_and_register_purchase_attempt

class TestPurchaseProcessor(TestBaseProcessorMixin, ConfiguringTestBase):

	def setUp(self):
		super(TestPurchaseProcessor, self).setUp()
		self.manager = PurchaseProcessor()

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
			user = create_random_user()
			username = user.username
			purchase_id = create_and_register_purchase_attempt(username, item=item,
															  quantity=2,
															  processor=self.manager.name)

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

		assert_that(eventtesting.getEvents(stripe_interfaces.IStripeCustomerCreated),
										   has_length(1))

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptStarted),
										   has_length(1))

		assert_that(eventtesting.getEvents(stripe_interfaces.IRegisterStripeToken),
										   has_length(1))
		assert_that(eventtesting.getEvents(stripe_interfaces.IRegisterStripeCharge),
										   has_length(1))

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptSuccessful),
										   has_length(1))

		with mock_dataserver.mock_db_trans(ds):
			user = User.get_user(username)
			su = stripe_interfaces.IStripeCustomer(user)
			akey = "%s.%s" % (su.__class__.__module__, su.__class__.__name__)
			self.manager.delete_customer(username)

		assert_that(eventtesting.getEvents(stripe_interfaces.IStripeCustomerDeleted),
										   has_length(1))

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

		assert_that(eventtesting.getEvents(stripe_interfaces.IStripeCustomerCreated),
					has_length(1))

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptStarted),
					has_length(1))

		assert_that(eventtesting.getEvents(stripe_interfaces.IRegisterStripeToken),
					has_length(1))
		assert_that(eventtesting.getEvents(stripe_interfaces.IRegisterStripeCharge),
					has_length(1))

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptSuccessful),
					has_length(1))

		c.delete()

	@WithMockDSTrans
	def test_fail_payment_invalid_token(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = create_random_user()
			username = user.username

		with mock_dataserver.mock_db_trans(ds):
			item = self.book_id
			purchase_id = create_and_register_purchase_attempt(username,
															   item=item,
															   processor=self.manager.name)

		with self.assertRaises(Exception):
			self.manager.process_purchase(username=username, token="++invalidtoken++",
										  purchase_id=purchase_id, expected_amount=100.0)

		assert_that(eventtesting.getEvents(stripe_interfaces.IStripeCustomerCreated),
					has_length(1))
		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptStarted),
					has_length(1))
		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptFailed),
					has_length(1))

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.State, is_(store_interfaces.PA_STATE_FAILED))

	@WithMockDSTrans
	def test_fail_payment_invalid_expected_amount(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = create_random_user()
			username = user.username

		with mock_dataserver.mock_db_trans(ds):
			item = self.book_id
			purchase_id = create_and_register_purchase_attempt(username,
															   item=item,
															   processor=self.manager.name)

		with self.assertRaises(Exception):
			self.manager.process_purchase(username=username, token="++valid++",
										  purchase_id=purchase_id, expected_amount=20000.0)

		assert_that(eventtesting.getEvents(store_interfaces.IPurchaseAttemptFailed),
					has_length(1))

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.State, is_(store_interfaces.PA_STATE_FAILED))
