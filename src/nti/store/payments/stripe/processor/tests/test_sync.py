#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that

import stripe
import unittest

from nti.store.payments.stripe import interfaces as stripe_interfaces

from nti.store import purchase_history
from nti.store import interfaces as store_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from ..sync import SyncProcessor
from ..purchase import PurchaseProcessor

from . import create_purchase
from . import TEST_WITH_STRIPE
from . import create_random_user
from . import ConfiguringTestBase
from . import TestBaseProcessorMixin
from . import create_and_register_purchase_attempt

class TestSyncProcessor(TestBaseProcessorMixin, ConfiguringTestBase):

	def setUp(self):
		super(TestSyncProcessor, self).setUp()
		self.manager = SyncProcessor()
		self.purchase = PurchaseProcessor()

	create_purchase = create_purchase

	@unittest.skipUnless(TEST_WITH_STRIPE, '')
	@WithMockDSTrans
	def test_sync_pending_purchase(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			username, purchase_id, tid, cid = self.create_purchase(manager=self.purchase)

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchaseAttempt(pa)
			assert_that(sp.token_id, is_(tid))
			assert_that(sp.charge_id, is_(cid))

			# change state for synching
			pa.State = store_interfaces.PA_STATE_STARTED

		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username,
												api_key=stripe.api_key)
			assert_that(charge, is_not(None))

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.State, is_(store_interfaces.PA_STATE_SUCCESS))

	@unittest.skipUnless(TEST_WITH_STRIPE, '')
	@WithMockDSTrans
	def test_sync_invalid_charge_id(self):
		ds = self.ds
		username, purchase_id, _, _ = self.create_purchase(manager=self.purchase)

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
		username, purchase_id, _, _ = self.create_purchase(manager=self.purchase)

		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchaseAttempt(pa)
			sp.charge_id = None

		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username,
												api_key=stripe.api_key)
			assert_that(charge, is_not(None))

	@unittest.skipUnless(TEST_WITH_STRIPE, '')
	@WithMockDSTrans
	def test_sync_with_tokens(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = create_random_user()
			username = user.username

		with mock_dataserver.mock_db_trans(ds):
			item = self.book_id
			purchase_id = create_and_register_purchase_attempt(username,
															   item=item,
															   processor=self.manager.name)

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
