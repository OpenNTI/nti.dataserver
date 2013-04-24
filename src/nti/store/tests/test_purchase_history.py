#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time

from nti.dataserver.users import User
from nti.externalization.oids import to_external_ntiid_oid

from nti.store import purchase_order
from nti.store import purchase_attempt
from nti.store import purchase_history
from nti.store import interfaces as store_interfaces

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_length, none, not_none)

class TestPurchaseHistory(ConfiguringTestBase):

	processor = 'stripe'

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	def _create_purchase_attempt(self, item=u'xyz-book', quantity=None, state=store_interfaces.PA_STATE_UNKNOWN):
		pi = purchase_order.create_purchase_item(item, 1)
		po = purchase_order.create_purchase_order(pi, quantity=quantity)
		pa = purchase_attempt.create_purchase_attempt(po, processor=self.processor, state=state)
		return pa

	@WithMockDSTrans
	def test_purchase_hist(self):
		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)
		assert_that(hist, is_(not_none()))

		pa_1 = self._create_purchase_attempt()
		hist.add_purchase(pa_1)
		assert_that(hist, has_length(1))

		assert_that(pa_1.id, is_(not_none()))

		pa_2 = self._create_purchase_attempt('zky')
		hist.add_purchase(pa_2)
		assert_that(hist, has_length(2))

		assert_that(list(hist.values()), has_length(2))

		t = (pa_1, pa_2)
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

		item = u'xyz-book'
		pending = self._create_purchase_attempt(item, state=store_interfaces.PA_STATE_STARTED)
		hist.add_purchase(pending)

		pa = purchase_history.get_pending_purchase_for(user, item)
		assert_that(pa, is_(not_none()))
		assert_that(pa, is_(pending))

	@WithMockDSTrans
	def test_missing_purchase(self):
		user = self._create_user()
		purchase_id = u'tag:nextthought.com,2011-10:system-OID-0x06cdce28af3dc253:0000000073:XVq3tFG7T82'
		pa = purchase_history.get_purchase_attempt(purchase_id, user)
		assert_that(pa, is_(none()))

	@mock_dataserver.WithMockDS
	def test_purchase_history(self):
		now = time.time()
		t50 = 0
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			username = user.username

		def _get_hist():
			user = User.get_user(username)
			hist = store_interfaces.IPurchaseHistory(user)
			return hist

		for i in range(0, 100):
			item = unicode(i)
			if i == 50:
				t50 = time.time()
			with mock_dataserver.mock_db_trans(self.ds):
				hist = _get_hist()
				pa = self._create_purchase_attempt(item)
				hist.add_purchase(pa)
				hist._v_check()

		with mock_dataserver.mock_db_trans(self.ds):
			hist = _get_hist()
			hist._v_check()

			assert_that(hist, has_length(100))

			lst = list(hist.get_purchase_history())
			assert_that(lst, has_length(100))

			lst = list(hist.get_purchase_history(end_time=now))
			assert_that(lst, has_length(0))

			lst = list(hist.get_purchase_history(start_time=now))
			assert_that(lst, has_length(100))

			lst = list(hist.get_purchase_history(start_time=now, end_time=t50))
			assert_that(lst, has_length(50))
			
			lst = list(hist.get_purchase_history(start_time=now, end_time=t50))
			assert_that(lst, has_length(50))

			lst = list(hist.get_purchase_history_by_item(u'10'))
			assert_that(lst, has_length(1))
			
