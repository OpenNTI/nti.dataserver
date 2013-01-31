from __future__ import unicode_literals, print_function, absolute_import

import uuid
import stripe
import unittest

from nti.dataserver.users import User
from nti.dataserver.users import interfaces as user_interfaces

from nti.store.payments import _stripe as nti_stripe
from nti.store.payments import interfaces as pay_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.payments.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_entry, has_length)

class _BaseTestStripe(object):
	
	@classmethod
	def setUpClass(cls):
		cls.api_key = stripe.api_key
		stripe.api_key = u'sk_test_0x3LXvPmdaWpr4KbNXtii3cL'
		
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
	
class TestStripeCustomer(_BaseTestStripe, ConfiguringTestBase):
		
	@WithMockDSTrans
	def test_adapter(self):
		user = self._create_user()
		adapted = pay_interfaces.IStripeCustomer(user)
		assert_that(adapted, is_not(None))
		assert_that(adapted.customer_id, is_(None))
		assert_that(adapted.card, is_(None))
		adapted.card = 'foo'
		adapted.customer_id = 'xyz'
		assert_that(adapted.id, is_('xyz'))
		assert_that(adapted.customer_id, is_('xyz'))
		assert_that(adapted.card, is_('foo'))
		adapted.add_charge('x','y')
		assert_that(adapted.charges, has_entry('x','y'))
		adapted.clear()
		assert_that(adapted.charges, has_length(0))
		assert_that(adapted.customer_id, is_(None))
		assert_that(adapted.card, is_(None))
		
@unittest.SkipTest
class TestStripeOps(_BaseTestStripe, ConfiguringTestBase):
	
	@classmethod
	def setUpClass(cls):
		_BaseTestStripe.setUpClass()
		cls.customers = set()
	
	@classmethod
	def tearDownClass(cls):
		_BaseTestStripe.tearDownClass()
		for cid in cls.customers:
			try:
				nti_stripe.delete_stripe_customer(cid)
			except:
				pass
		
	@WithMockDSTrans
	def test_create_update_delete_customer(self):
		user = self._create_random_user()
		adapted, scust = nti_stripe.get_or_create_customer(user)
		
		assert_that(scust, is_not(None))
		assert_that(adapted.customer_id, is_not(None))
		
		profile = user_interfaces.IUserProfile(user)
		setattr(profile, 'email', 'xyz@nt.com')
		r = nti_stripe.update_customer(user, scust)
		assert_that(r, is_(True))
		
		r = nti_stripe.delete_customer(user)
		assert_that(r, is_(True))
		adapted = pay_interfaces.IStripeCustomer(user)
		assert_that(adapted.customer_id, is_(None))
		assert_that(adapted.card, is_(None))
		assert_that(adapted.charges, has_length(0))
		
	@WithMockDSTrans
	def test_create_token_and_charge(self):
		t = nti_stripe.create_card_token(number="5105105105105100", 
										 exp_month="11",
										 exp_year="30",
										 cvc="542",
										 address="3001 Oak Tree #D16",
										 city="Norman",
										 zip = "73072",
										 state="OK",
										 country="USA")
		assert_that(t, is_not(None))
		c = nti_stripe.create_charge(100, card=t, description="my charge")
		assert_that(c, is_not(None))
		
	@WithMockDSTrans
	def test_process_payment(self):
		user = self._create_random_user()
		t = nti_stripe.create_card_token(number="5105105105105100", 
										 exp_month="11",
										 exp_year="30",
										 cvc="542",
										 address="3001 Oak Tree #D16",
										 city="Norman",
										 zip = "73072",
										 state="OK",
										 country="USA")
		cid = nti_stripe.process_payment(user, token=t, amount=100,
										 currency='USD', description="my payment")
		
		assert_that(cid, is_not(None))
		
		adapted = pay_interfaces.IStripeCustomer(user)
		assert_that(adapted.card, is_not(None))
		
		nti_stripe.delete_customer(user)
		
if __name__ == '__main__':
	unittest.main()
