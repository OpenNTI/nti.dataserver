#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope.schema import vocabulary

from nti.dataserver.users import User

from ..import purchasable
from .. import purchase_attempt
from .. import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_key, has_length, is_not, none, is_, is_in, greater_than_or_equal_to)

class TestPurchasable(ConfiguringTestBase):

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	def test_zmcl(self):
		voc = vocabulary.getVocabularyRegistry().get(None, store_interfaces.PURCHASABLE_VOCAB_NAME)
		assert_that(voc, is_not(none()))

		util = purchasable.PurchasableUtilityVocabulary(None)
		assert_that(util, has_length(greater_than_or_equal_to(4)))

		assert_that(util.getTermByToken('iid_0'), is_not(none()))

		ps = util.getTermByToken('iid_3').value
		assert_that(ps.NTIID, "iid_3")
		assert_that(ps.Title, "Risk Course")
		assert_that(ps.Title, "Risk Course")
		assert_that(ps.Description, "Intro to Risk")
		assert_that(ps.Provider, "PRMIA")
		assert_that(ps.Amount, 90)
		assert_that(ps.Currency, "USD")
		assert_that(ps.Discountable, is_(True))
		assert_that(ps.BulkPurchase, is_(False))
		assert_that(ps.Items, has_length(2))

	@WithMockDSTrans
	def test_available(self):
		self._create_user()
		m = purchasable.get_available_items('nt@nti.com')
		assert_that(m, has_key('iid_1'))
		assert_that(m, has_key('iid_2'))

	@WithMockDSTrans
	def test_purchased(self):
		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)
		pa = purchase_attempt.create_purchase_attempt(items=("iid_3",), processor="stripe",
													  state=store_interfaces.PA_STATE_SUCCESS)
		hist.add_purchase(pa)

		m = purchasable.get_available_items('nt@nti.com')
		assert_that(m, is_not(has_key('iid_3')))

	def test_get_content_items(self):
		items = purchasable.get_content_items("iid_3")
		assert_that(items, has_length(2))
		assert_that('var-risk', is_in(items))
		assert_that('volatility', is_in(items))
