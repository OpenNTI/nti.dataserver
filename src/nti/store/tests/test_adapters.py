from __future__ import unicode_literals, print_function, absolute_import

import unittest

from nti.dataserver.users import User

from nti.store import interfaces as store_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_not)	
	
class TestCustomerAdapter(ConfiguringTestBase):
		
	def _create_user(self, username='nt@nti.com', password='temp001', **kwargs):
		ds = mock_dataserver.current_mock_ds
		ext_value = {'external_value':kwargs}
		usr = User.create_user( ds, username=username, password=password, **ext_value)
		return usr
	
	@WithMockDSTrans
	def test_purchase_hist(self):
		user = self._create_user()
		adapted = store_interfaces.IPurchaseHistory(user)
		assert_that(adapted, is_not(None))
			
if __name__ == '__main__':
	unittest.main()
