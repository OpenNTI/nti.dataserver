from __future__ import unicode_literals, print_function, absolute_import

import unittest

from nti.dataserver.users import User

from nti.store.payments import interfaces as pay_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.payments.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_entry, has_length)

class TestStripe(ConfiguringTestBase):
	
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
	
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
		
		
if __name__ == '__main__':
	unittest.main()