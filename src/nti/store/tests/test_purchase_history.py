#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import unittest

import zope.intid
from zope import component

from nti.dataserver.users import User
from nti.externalization.oids import to_external_ntiid_oid

from nti.store import purchase
from nti.store import purchase_history
from nti.store import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_length)

class TestPurchaseHistoryAdapter(ConfiguringTestBase):

	processor = 'stripe'

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user( self.ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_purchase_hist(self):
		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)
		assert_that(hist, is_not(None))

		pa = purchase.create_purchase_attempt('xyz', self.processor)
		hist.add_purchase(pa)
		assert_that(hist, has_length(1))

		assert_that(pa.id, is_not(None))

		intids = component.queryUtility( zope.intid.IIntIds )
		assert_that(intids.queryId(pa), is_not(None))

		pa = purchase.create_purchase_attempt('xyz', self.processor)
		hist.add_purchase(pa)
		assert_that(hist, has_length(2))

		oid = to_external_ntiid_oid(pa)
		assert_that(hist.get_purchase(oid), is_(pa))

		hist.remove_purchase(pa)
		assert_that(hist, has_length(1))
		
	@WithMockDSTrans
	def test_missing_purchase(self):
		user = self._create_user()
		purchase_id = u'tag:nextthought.com,2011-10:system-OID-0x06cdce28af3dc253:0000000073:XVq3tFG7T82'
		pa = purchase_history.get_purchase_attempt(purchase_id, user)
		assert_that(pa, is_(None))
		
if __name__ == '__main__':
	unittest.main()
	
