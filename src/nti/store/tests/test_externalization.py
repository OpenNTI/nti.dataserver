#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os

from zope import component

from nti.contentlibrary.interfaces import IFilesystemContentPackageLibrary
from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary

from nti.dataserver.users import User

from nti.externalization.externalization import to_external_object

from .. import purchase_attempt
from ..import priced_purchasable
from ..import purchasable_store as store
from .. import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_key, has_entry, none)

class TestStoreExternal(ConfiguringTestBase):

	set_up_packages = ConfiguringTestBase.set_up_packages + (('purchasables.zcml', 'nti.store.tests'),)

	processor = 'stripe'

	def setUp(self):
		library = FileLibrary(os.path.join(os.path.dirname(__file__), 'library'))
		component.provideUtility(library, IFilesystemContentPackageLibrary)

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_purchase_hist(self):
		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)

		pa = purchase_attempt.create_purchase_attempt(items='xyz', processor=self.processor,
													  description='my charge', quantity=2)
		hist.add_purchase(pa)

		ext = to_external_object(pa)
		assert_that(ext, has_key('MimeType'))
		assert_that(ext, has_entry('Class', u'PurchaseAttempt'))
		assert_that(ext, has_entry('Items', ['xyz']))
		assert_that(ext, has_entry('State', 'Unknown'))
		assert_that(ext, has_entry('OID', is_not(None)))
		assert_that(ext, has_entry('Last Modified', is_not(None)))
		assert_that(ext, has_entry('Processor', self.processor))
		assert_that(ext, has_entry('StartTime', is_not(None)))
		assert_that(ext, has_entry('EndTime', is_(None)))
		assert_that(ext, has_entry('Error', is_(None)))
		assert_that(ext, has_entry('Description', is_('my charge')))
		assert_that(ext, has_entry('Quantity', is_(2)))
		assert_that(ext, has_entry('InvitationCode', is_not(none())))

	def test_purchasable(self):
		util = store.PurchasableUtilityVocabulary(None)
		ps = util.getTermByToken('iid_3').value
		ext = to_external_object(ps)

		assert_that(ext, has_key('MimeType'))
		assert_that(ext, has_entry('NTIID', u'iid_3'))
		assert_that(ext, has_entry('Class', u'Purchasable'))
		assert_that(ext, has_entry('Amount', 90))
		assert_that(ext, has_entry('Currency', u'USD'))
		assert_that(ext, has_entry('BulkPurchase', False))
		assert_that(ext, has_entry('Discountable', True))
		assert_that(ext, has_entry('Provider', u'PRMIA'))
		assert_that(ext, has_entry('Title', u'Risk Course'))
		assert_that(ext, has_entry('Author', u'Alan Laubsch'))
		assert_that(ext, has_entry('Icon', u'http://prmia.org/'))
		assert_that(ext, has_entry('Description', u'Intro to Risk'))

	def test_priced_purchasable(self):
		pp = priced_purchasable.create_priced_purchasable(u'iid_3', 100, 2)
		ext = to_external_object(pp)
		assert_that(ext, has_key('MimeType'))
		assert_that(ext, is_not(has_key('PurchaseFee')))
		assert_that(ext, is_not(has_key('NonDiscountedPrice')))
		assert_that(ext, has_entry('Provider', u'PRMIA'))
		assert_that(ext, has_entry('PurchasePrice', 100))
		assert_that(ext, has_entry('Class', u'PricedPurchasable'))

		pp = priced_purchasable.create_priced_purchasable(u'iid_3', 200, 30, 20)
		ext = to_external_object(pp)
		assert_that(ext, is_not(has_key('PurchaseFee')))
		assert_that(ext, has_entry('NonDiscountedPrice', 20))
		assert_that(ext, has_entry('PurchasePrice', 200))

	def test_fill_in_lib(self):
		pe = store.create_purchasable(ntiid='tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.cosmetology',
									  provider='MLC',
									  amount=100)
		ext = to_external_object(pe)
		assert_that(ext, has_entry('Title', u'COSMETOLOGY'))
		assert_that(ext, has_entry('Description', u'COSMETOLOGY'))
