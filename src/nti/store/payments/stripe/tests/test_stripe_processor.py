#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import time
import uuid
import stripe

from zope import component
from zope.annotation import IAnnotations

from nti.dataserver.users import User

from .... import purchase_attempt
from .... import purchase_history
from .. import interfaces as stripe_interfaces
from .... import interfaces as store_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from zope.component import eventtesting
from hamcrest import (assert_that, is_, is_not, has_length, has_key)

class TestStripeProcessor(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestStripeProcessor,cls).setUpClass()
		cls.api_key = stripe.api_key
		stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'

	def setUp( self ):
		super(TestStripeProcessor,self).setUp()
		self.manager = component.getUtility(store_interfaces.IPaymentProcessor, name='stripe')

	@classmethod
	def tearDownClass(cls):
		super(TestStripeProcessor,cls).tearDownClass()
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

	def create_purchase(self, items=('xyz',), amount=100):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = self._create_random_user()
			username = user.username
		
		with mock_dataserver.mock_db_trans(ds):
			items = ('xyz book',)
			pa = purchase_attempt.create_purchase_attempt(items=items, processor=self.manager.name, description="my charge")
			purchase_id = purchase_history.register_purchase_attempt(username, pa)
			assert_that(purchase_id, is_not(None))
				
		tid = self.manager.create_card_token(number="5105105105105100",
										 	 exp_month="11",
										 	 exp_year="30",
										 	 cvc="542",
										 	 address="3001 Oak Tree #D16",
										 	 city="Norman",
										 	 zip = "73072",
										 	 state="OK",
										 	 country="USA")
		
		cid = self.manager.process_purchase(username=username, token=tid,
											purchase_id=purchase_id, amount=amount, currency='USD')
		
		assert_that(tid, is_not(None))
		assert_that(cid, is_not(None))
		
		return username, purchase_id, tid, cid 
										
	@WithMockDSTrans
	def test_process_payment(self):
		ds = self.ds
		username, purchase_id, _, _ = self.create_purchase()
		
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.state, is_(store_interfaces.PA_STATE_SUCCESS))

		assert_that( eventtesting.getEvents(stripe_interfaces.IStripeCustomerCreated), has_length( 1 ) )

		assert_that(eventtesting.getEvents( store_interfaces.IPurchaseAttemptStarted ), has_length( 1 ) )

		assert_that(eventtesting.getEvents( stripe_interfaces.IRegisterStripeToken ), has_length( 1 ) )
		assert_that(eventtesting.getEvents( stripe_interfaces.IRegisterStripeCharge ), has_length( 1 ) )
		
		assert_that(eventtesting.getEvents( store_interfaces.IPurchaseAttemptSuccessful ), has_length( 1 ) )

		with mock_dataserver.mock_db_trans(ds):
			user = User.get_user(username)
			su = stripe_interfaces.IStripeCustomer(user)
			akey = "%s.%s" % (su.__class__.__module__, su.__class__.__name__)
			self.manager.delete_customer(username)
		assert_that( eventtesting.getEvents(stripe_interfaces.IStripeCustomerDeleted), has_length( 1 ) )
		
		with mock_dataserver.mock_db_trans(ds):
			user = User.get_user(username)
			assert_that(IAnnotations(user), is_not(has_key(akey)))
		
	@WithMockDSTrans
	def test_sync_pending_purchase(self):		
		ds = self.ds
		username, purchase_id, tid, cid = self.create_purchase()
			
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchase(pa)
			assert_that(sp.token_id, is_(tid))
			assert_that(sp.charge_id, is_(cid))
			
			# change state for synching
			pa.state = store_interfaces.PA_STATE_STARTED
			
		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username)
			assert_that(charge, is_not(None))
			
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			assert_that(pa.state, is_(store_interfaces.PA_STATE_SUCCESS))
			
	@WithMockDSTrans
	def test_sync_invalid_charge_id(self):		
		ds = self.ds
		username, purchase_id, _, _ = self.create_purchase()
		
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchase(pa)
			sp.charge_id = 'invalid'
			
		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username)
			assert_that(charge, is_(None))
			
	@WithMockDSTrans
	def test_sync_invalid_missing_charge_id(self):		
		ds = self.ds
		username, purchase_id, _, _ = self.create_purchase()
		
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchase(pa)
			sp.charge_id = None
			
		with mock_dataserver.mock_db_trans(ds):
			charge = self.manager.sync_purchase(purchase_id, username=username)
			assert_that(charge, is_not(None))

	@WithMockDSTrans
	def test_sync_with_tokens(self):		
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = self._create_random_user()
			username = user.username
			
		with mock_dataserver.mock_db_trans(ds):
			items = ('xyz book',)
			pa = purchase_attempt.create_purchase_attempt(items=items, processor=self.manager.name, description="my charge")
			purchase_id = purchase_history.register_purchase_attempt(username, pa)
			
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
										 	 zip = "73072",
										 	 state="OK",
										 	 country="USA")
		
		# unused token
		with mock_dataserver.mock_db_trans(ds):
			pa = purchase_history.get_purchase_attempt(purchase_id, username)
			sp = stripe_interfaces.IStripePurchase(pa)
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
		c.amount_off = 200
		amt = self.manager.apply_coupon(amount, c)
		assert_that(amt, is_(800))
