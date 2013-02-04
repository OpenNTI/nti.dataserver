from __future__ import unicode_literals, print_function, absolute_import

import unittest

from nti.dataserver.users import User

from nti.externalization.externalization import to_external_object

from nti.store import purchase
from nti.store import interfaces as store_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_entry)	
	
class TestStoreExternal(ConfiguringTestBase):
		
	processor = store_interfaces.STRIPE_PROCESSOR
	
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
	
	@WithMockDSTrans
	def test_purchase_hist(self):		
		user = self._create_user()		
		hist = store_interfaces.IPurchaseHistory(user, None)
		
		pa = purchase.create_purchase_attempt('xyz', self.processor)
		hist.add_purchase(pa)
		
		ext = to_external_object(pa)
		assert_that(ext,  has_entry('Class', u'PurchaseAttempt'))
		assert_that(ext,  has_entry('Items', ['xyz']))
		assert_that(ext,  has_entry('State','Started'))
		assert_that(ext,  has_entry('OID', is_not(None)))
		assert_that(ext,  has_entry('Last Modified', is_not(None)))
		assert_that(ext,  has_entry('Processor', 'stripe'))
		assert_that(ext,  has_entry('StartTime', is_not(None)))
		assert_that(ext,  has_entry('EndTime', is_(None)))
		assert_that(ext,  has_entry('ErrorMessage', is_(None)))
			
if __name__ == '__main__':
	unittest.main()
