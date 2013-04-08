#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver.users import User

from nti.externalization.externalization import to_external_object

from .. import purchase_attempt
from ..import purchasable_store as store
from .. import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_entry)

class TestStoreExternal(ConfiguringTestBase):

	set_up_packages = ConfiguringTestBase.set_up_packages + (('purchasables.zcml', 'nti.store.tests'),)

	processor = 'stripe'

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_purchase_hist(self):
		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)

		pa = purchase_attempt.create_purchase_attempt(items='xyz', processor=self.processor,
													  description='my charge', on_behalf_of='foo')
		hist.add_purchase(pa)

		ext = to_external_object(pa)
		assert_that(ext, has_entry('Class', u'PurchaseAttempt'))
		assert_that(ext, has_entry('Items', ['xyz']))
		assert_that(ext, has_entry('State', 'Unknown'))
		assert_that(ext, has_entry('OID', is_not(None)))
		assert_that(ext, has_entry('Last Modified', is_not(None)))
		assert_that(ext, has_entry('Processor', self.processor))
		assert_that(ext, has_entry('StartTime', is_not(None)))
		assert_that(ext, has_entry('EndTime', is_(None)))
		assert_that(ext, has_entry('ErrorMessage', is_(None)))
		assert_that(ext, has_entry('Description', is_('my charge')))
		assert_that(ext, has_entry('OnBehalfOf', is_(['foo'])))

	def test_purchasable(self):
		util = store.PurchasableUtilityVocabulary(None)
		ps = util.getTermByToken('iid_3').value
		ext = to_external_object(ps)

		assert_that(ext, has_entry('NTIID', u'iid_3'))
		assert_that(ext, has_entry('Class', u'Purchasable'))
		assert_that(ext, has_entry('Amount', 90))
		assert_that(ext, has_entry('Currency', u'USD'))
		assert_that(ext, has_entry('BulkPurchase', False))
		assert_that(ext, has_entry('Discountable', True))
		assert_that(ext, has_entry('Provider', u'PRMIA'))
		assert_that(ext, has_entry('Title', u'Risk Course'))
		assert_that(ext, has_entry('URL', u'http://prmia.org/'))
		assert_that(ext, has_entry('Description', u'Intro to Risk'))
