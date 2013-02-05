#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import uuid
import stripe
import unittest

from zope import component

from nti.dataserver.users import User

from nti.store import purchase
from nti.store import purchase_history
from nti.store import interfaces as store_interfaces
from nti.store.payments import interfaces as pay_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans, WithMockDS

from nti.store.tests import ConfiguringTestBase

from zope.component import eventtesting
from hamcrest import (assert_that, is_, is_not, has_length)

@unittest.SkipTest
class TestStripeIO(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		cls.api_key = stripe.api_key
		stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'

	def setUp( self ):
		super(ConfiguringTestBase,self).setUp()
		self.manager = component.getUtility(store_interfaces.IPaymentProcessor, name='stripe')

	@classmethod
	def tearDownClass(cls):
		stripe.api_key = cls.api_key

	def _create_user(self, username='nt@nti.com', password='temp001', **kwargs):
		ds = mock_dataserver.current_mock_ds
		ext_value = {'external_value':kwargs}
		usr = User.create_user( ds, username=username, password=password, **ext_value)
		return usr

	def _create_random_user(self):
		code =  str(uuid.uuid4()).split('-')[0]
		username = u'u' + code
		email = username + '@nextthought.com'
		desc = 'test user ' +  code
		user = self._create_user(username=username, email=email, description=desc)
		return user

	@WithMockDSTrans
	def test_create_token_and_charge(self):
		t = self.manager.create_card_token(	number="5105105105105100",
											exp_month="11",
											exp_year="30",
											cvc="542",
											address="3001 Oak Tree #D16",
											city="Norman",
											zip = "73072",
											state="OK",
											country="USA")
		assert_that(t, is_not(None))
		c = self.manager.create_charge(100, card=t, description="my charge")
		assert_that(c, is_not(None))

	def create_purchase(self, username, purchase_id, amount=100):
		t = self.manager.create_card_token(	number="5105105105105100",
										 	exp_month="11",
										 	exp_year="30",
										 	cvc="542",
										 	address="3001 Oak Tree #D16",
										 	city="Norman",
										 	zip = "73072",
										 	state="OK",
										 	country="USA")
		
		cid = self.manager.process_purchase(username=username, token=t,
											purchase_id=purchase_id, amount=amount, currency='USD')
		return t, cid
										
	@WithMockDS
	def test_process_payment(self):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = self._create_random_user()
			username = user.username
		
		with mock_dataserver.mock_db_trans(ds):
			items = ('xyz book',)
			pa = purchase.create_purchase_attempt(items, self.manager.name, description="my charge")
			purchase_id = purchase_history.register_purchase_attempt(username, pa)
			assert_that(purchase_id, is_not(None))
			
		with mock_dataserver.mock_db_trans(ds):
			tid, cid = self.create_purchase(username, purchase_id, 1000)
		
		assert_that(tid, is_not(None))
		assert_that(cid, is_not(None))
		
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.state, is_(store_interfaces.PA_STATE_SUCCESSFUL))

		assert_that( eventtesting.getEvents(pay_interfaces.IStripeCustomerCreated), has_length( 1 ) )

		assert_that(eventtesting.getEvents( store_interfaces.IPurchaseAttemptStarted ), has_length( 1 ) )

		assert_that(eventtesting.getEvents( pay_interfaces.IRegisterStripeToken ), has_length( 1 ) )
		assert_that(eventtesting.getEvents( pay_interfaces.IRegisterStripeCharge ), has_length( 1 ) )
		
		assert_that(eventtesting.getEvents( store_interfaces.IPurchaseAttemptSuccessful ), has_length( 1 ) )

		with mock_dataserver.mock_db_trans(ds):
			self.manager.delete_customer(username)
		assert_that( eventtesting.getEvents(pay_interfaces.IStripeCustomerDeleted), has_length( 1 ) )
		
		with mock_dataserver.mock_db_trans(ds):
			user = User.get_user(username)
			su = pay_interfaces.IStripeCustomer(user)	
			assert_that(su.customer_id, is_(None))
		
	@WithMockDSTrans
	def test_sync_pending_purchase(self):		
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = self._create_random_user()
			username = user.username
			
		with mock_dataserver.mock_db_trans(ds):
			items = ('xyz book',)
			pa = purchase.create_purchase_attempt(items, self.manager.name, description="my charge")
			purchase_id = purchase_history.register_purchase_attempt(username, pa)
			assert_that(purchase_id, is_not(None))
			
		with mock_dataserver.mock_db_trans(ds):
			t, cid = self.create_purchase(username, purchase_id, 1000)
			
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = pay_interfaces.IStripePurchase(pa)
			assert_that(sp.token_id, is_(t))
			assert_that(sp.charge_id, is_(cid))
			# change state 
			pa.state = store_interfaces.PA_STATE_STARTED
			
		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username)
			assert_that(charge, is_not(None))
			
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.state, is_(store_interfaces.PA_STATE_SUCCESSFUL))
		
if __name__ == '__main__':
	unittest.main()
