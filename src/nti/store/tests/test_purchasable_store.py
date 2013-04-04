#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import component

from nti.dataserver.users import User

from .. import purchase_attempt
from ..import purchasable_store as store
from ..purchasable import create_purchasable
from .. import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_entry, has_key, is_not, none)

class TestPurchasableStore(ConfiguringTestBase):

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	def test_empty(self):
		m = store.get_purchasables()
		assert_that(m, is_not(none()))

	def test_register(self):
		p = create_purchasable("iid_0", "item", "provider", "title", "desc", 100)
		component.getGlobalSiteManager().registerUtility(p, store_interfaces.IPurchasable, "iid_0")
		m = store.get_purchasables()
		assert_that(m, has_entry('iid_0', p))

	@WithMockDSTrans
	def test_available(self):
		self._create_user()
		p = create_purchasable("iid_1", "item", "provider", "title", "desc", 100)
		component.getGlobalSiteManager().registerUtility(p, store_interfaces.IPurchasable, "iid_1")
		p = create_purchasable("iid_2", "item", "provider", "title", "desc", 100)
		component.getGlobalSiteManager().registerUtility(p, store_interfaces.IPurchasable, "iid_2")
		m = store.get_available_items(store, 'nt@nti.com')
		assert_that(m, has_key('iid_1'))
		assert_that(m, has_entry('iid_2', p))

	@WithMockDSTrans
	def test_purchased(self):
		p = create_purchasable("iid_3", "item", "provider", "title", "desc", 100)
		component.getGlobalSiteManager().registerUtility(p, store_interfaces.IPurchasable, "iid_2")

		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)
		pa = purchase_attempt.create_purchase_attempt(items=("iid_3",), processor="stripe",
													  state=store_interfaces.PA_STATE_SUCCESS)
		hist.add_purchase(pa)

		m = store.get_available_items(store, 'nt@nti.com')
		assert_that(m, is_not(has_key('iid_3')))
