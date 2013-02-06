#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import unittest

import zope.intid
from zope import component

from nti.dataserver.users import User
from nti.externalization.oids import to_external_ntiid_oid

from nti.store import purchase_attempt
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

		pa_1 = purchase_attempt.create_purchase_attempt(items='xyz', processor=self.processor)
		hist.add_purchase(pa_1)
		assert_that(hist, has_length(1))

		assert_that(pa_1.id, is_not(None))

		intids = component.queryUtility( zope.intid.IIntIds )
		assert_that(intids.queryId(pa_1), is_not(None))

		pa_2 = purchase_attempt.create_purchase_attempt(items='zky', processor=self.processor)
		hist.add_purchase(pa_2)
		assert_that(hist, has_length(2))

		assert_that(list(hist.values()), has_length(2))
		
		t = (pa_1,pa_2)
		ck = all([c in t for c in hist])
		assert_that(ck, is_(True))
		
		oid = to_external_ntiid_oid(pa_2)
		assert_that(hist.get_purchase(oid), is_(pa_2))

		hist.remove_purchase(pa_2)
		assert_that(hist, has_length(1))
		
	@WithMockDSTrans
	def test_pending_purchase(self):
		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)

		items='xyz'
		pending = purchase_attempt.create_purchase_attempt(	items=items, processor=self.processor, 
															state=store_interfaces.PA_STATE_STARTED)
		hist.add_purchase(pending)

		pa = purchase_history.get_pending_purchase_for(user, items)
		assert_that(pa, is_not(None))
		assert_that(pa, is_(pending))

	@WithMockDSTrans
	def test_missing_purchase(self):
		user = self._create_user()
		purchase_id = u'tag:nextthought.com,2011-10:system-OID-0x06cdce28af3dc253:0000000073:XVq3tFG7T82'
		pa = purchase_history.get_purchase_attempt(purchase_id, user)
		assert_that(pa, is_(None))
		
if __name__ == '__main__':
	unittest.main()
	
