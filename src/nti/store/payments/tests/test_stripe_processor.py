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
from zope.lifecycleevent import IObjectCreatedEvent, IObjectRemovedEvent

from nti.dataserver.users import User
from nti.dataserver.users import interfaces as user_interfaces

from nti.store import purchase
from nti.store import interfaces as store_interfaces
from nti.store.payments import interfaces as pay_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

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
	def xtest_create_update_delete_customer(self):
		user = self._create_random_user()
		adapted, scust = self.manager.get_or_create_customer(user)
		assert_that(scust, is_not(None))
		assert_that(adapted.customer_id, is_not(None))

		profile = user_interfaces.IUserProfile(user)
		setattr(profile, 'email', 'xyz@nt.com')
		r = self.manager.update_customer(user, scust)
		assert_that(r, is_(True))

		r = self.manager.delete_customer(user)
		assert_that(r, is_(True))
		adapted = pay_interfaces.IStripeCustomer(user)
		assert_that(adapted.customer_id, is_(None))

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

	def create_purchase(self, user, purchase, amount=100):
		t = self.manager.create_card_token(	number="5105105105105100",
										 	exp_month="11",
										 	exp_year="30",
										 	cvc="542",
										 	address="3001 Oak Tree #D16",
										 	city="Norman",
										 	zip = "73072",
										 	state="OK",
										 	country="USA")
		cid = self.manager.process_purchase(user=user, token=t, purchase=purchase, amount=amount, currency='USD')
		return t, cid
										
	@WithMockDSTrans
	def test_process_payment(self):
		user = self._create_random_user()

		items = ('xyz book',)
		pa = purchase.create_purchase_attempt_and_start(user, items, 'stripe', description="my charge")
		assert_that(pa.state, is_(store_interfaces.PA_STATE_STARTED))

		tid, cid = self.create_purchase(user, pa, 1000)
		assert_that(tid, is_not(None))
		assert_that(cid, is_not(None))
		assert_that(pa.state, is_(store_interfaces.PA_STATE_SUCCESSFUL))

		assert_that( eventtesting.getEvents(IObjectCreatedEvent,
											lambda x: pay_interfaces.IStripeCustomer.providedBy(x.object)), has_length( 1 ) )

		assert_that(eventtesting.getEvents( store_interfaces.IPurchaseAttemptStarted ),
				 	has_length( 1 ) )

		assert_that(eventtesting.getEvents( store_interfaces.IPurchaseAttemptSuccessful ),
				 	has_length( 1 ) )

		self.manager.delete_customer(user)
		assert_that( eventtesting.getEvents( IObjectRemovedEvent,
											 lambda x: pay_interfaces.IStripeCustomer.providedBy(x.object) ), has_length( 1 ) )
		
	@WithMockDSTrans
	def test_sync_pending_purchase(self):		
		user = self._create_random_user()
			
		items=('xyz book',)
		pa = purchase.create_purchase_attempt_and_start(user, items, 'stripe', description="my charge")
		assert_that(pa.state, is_(store_interfaces.PA_STATE_STARTED))
			
		t, cid = self.create_purchase(user, pa, 1000)
	
		# mock_dataserver.current_transaction.commit(transaction.manager.get())
		sp = pay_interfaces.IStripePurchase(pa)
		assert_that(sp.token_id, is_(t))
		assert_that(sp.charge_id, is_(cid))
			
		pa.state = store_interfaces.PA_STATE_STARTED
		charge = self.manager.sync_purchase(pa, user=user)
		assert_that(charge, is_not(None))
		assert_that(pa.state, is_(store_interfaces.PA_STATE_SUCCESSFUL))
		
if __name__ == '__main__':
	unittest.main()
