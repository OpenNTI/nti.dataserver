from __future__ import unicode_literals, print_function, absolute_import

import uuid
import stripe
import unittest

from nti.dataserver.users import User

from nti.store.payments import _stripe as nti_stripe
from nti.store.payments import interfaces as pay_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.payments.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_entry, has_length)

class TestStripe(ConfiguringTestBase):
	
	@classmethod
	def setUpClass(cls):
		cls.api_key = stripe.api_key
		stripe.api_key = u'sk_test_0x3LXvPmdaWpr4KbNXtii3cL'
		cls.customers = set()
	
	@classmethod
	def tearDownClass(cls):
		stripe.api_key = cls.api_key
		for cid in cls.customers:
			try:
				nti_stripe.delete_stripe_customer(cid)
			except:
				pass
		
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
	def test_adapter(self):
		user = self._create_user()
		adapted = pay_interfaces.IStripeCustomer(user)
		assert_that(adapted, is_not(None))
		assert_that(adapted.customer_id, is_(None))
		assert_that(adapted.active_card, is_(None))
		adapted.active_card = 'foo'
		adapted.customer_id = 'xyz'
		assert_that(adapted.id, is_('xyz'))
		assert_that(adapted.customer_id, is_('xyz'))
		assert_that(adapted.active_card, is_('foo'))
		adapted.add_purchase('x','y')
		assert_that(adapted.purchases, has_entry('x','y'))
		adapted.clear()
		assert_that(adapted.purchases, has_length(0))
		assert_that(adapted.customer_id, is_(None))
		assert_that(adapted.active_card, is_(None))
		
	@WithMockDSTrans
	def test_create_update_delete_customer(self):
		user = self._create_random_user()
		adapted = nti_stripe.get_or_create_customer(user)
		assert_that(adapted.customer_id, is_not(None))
		
		r = nti_stripe.update_customer(user, "tok_jOq0M8vJprCUUU")
		assert_that(r, is_(True))
		adapted = pay_interfaces.IStripeCustomer(user)
		assert_that(adapted.active_card, is_("tok_jOq0M8vJprCUUU"))
		
		r = nti_stripe.delete_customer(user)
		assert_that(r, is_(True))
		adapted = pay_interfaces.IStripeCustomer(user)
		assert_that(adapted.customer_id, is_(None))
		assert_that(adapted.active_card, is_(None))
		assert_that(adapted.purchases, has_length(0))
		
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
		
if __name__ == '__main__':
	unittest.main()
