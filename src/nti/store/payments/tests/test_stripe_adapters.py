from __future__ import unicode_literals, print_function, absolute_import

import unittest

from nti.dataserver.users import User

from nti.store import purchase
from nti.store.payments import interfaces as pay_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not)
		
class TestStripeAdapters(ConfiguringTestBase):
		
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
	
	@WithMockDSTrans
	def test_stripe_customer_adapter(self):
		user = self._create_user()
		adapted = pay_interfaces.IStripeCustomer(user)
		assert_that(adapted, is_not(None))
		assert_that(adapted.customer_id, is_(None))
		
		adapted.customer_id = 'xyz'
		assert_that(adapted.customer_id, is_('xyz'))
		
	@WithMockDSTrans
	def test_stripe_purchase_adapter(self):
		items = ('xyz',)
		pa = purchase.create_purchase_attempt(items, 'stripe')
		adapted = pay_interfaces.IStripePurchase(pa)
		adapted.charge_id = 'charge_id'
		adapted.token_id = 'token_id'
		assert_that(adapted.purchase, is_(pa))
		assert_that(adapted.charge_id, is_('charge_id'))
		assert_that(adapted.token_id, is_('token_id'))
					
if __name__ == '__main__':
	unittest.main()
