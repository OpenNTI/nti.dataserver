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

from ..import pricing
from ..import priceable
from ..import purchasable
from .. import purchase_order
from .. import purchase_attempt
from .. import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_key, has_entry, has_length, none)

class TestStoreExternal(ConfiguringTestBase):

	set_up_packages = ConfiguringTestBase.set_up_packages + (('purchasables.zcml', 'nti.store.tests'),)

	processor = 'stripe'

	def setUp(self):
		library = FileLibrary(os.path.join(os.path.dirname(__file__), 'library'))
		component.provideUtility(library, IFilesystemContentPackageLibrary)

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	def _create_purchase_attempt(self, item=u'xyz-book', quantity=None,
								 state=store_interfaces.PA_STATE_UNKNOWN,
								 description='my purchase'):
		po = purchase_order.create_purchase_item(item, 1)
		purchase_order.create_purchase_order(po, quantity=quantity)
		# pa = purchase_attempt.create_purchase_attempt(po, processor=self.processor)
		pa = purchase_attempt.create_purchase_attempt(item, quantity=quantity,
													  processor=self.processor,
													  description=description,
													  state=state)
		return pa

	@WithMockDSTrans
	def test_purchase_hist(self):
		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)

		pa = self._create_purchase_attempt(description='my charge', quantity=2)
		hist.add_purchase(pa)

		ext = to_external_object(pa)
		assert_that(ext, has_key('MimeType'))
		assert_that(ext, has_entry('Class', u'PurchaseAttempt'))
		assert_that(ext, has_entry('Items', ['xyz-book']))
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

	@WithMockDSTrans
	def test_purchase_order(self):
		pi_1 = purchase_order.create_purchase_item("ichigo", 1)
		pi_2 = purchase_order.create_purchase_item("aizen", 2)
		po = purchase_order.create_purchase_order((pi_1, pi_2))
		ext = to_external_object(po)
		assert_that(ext, has_entry('Items', has_length(2)))
		assert_that(ext, has_entry('Quantity', is_(none())))
		items = ext['Items']
		assert_that(items[0], has_entry('NTIID', 'ichigo'))
		assert_that(items[0], has_entry('Quantity', 1))
		assert_that(items[1], has_entry('NTIID', 'aizen'))
		assert_that(items[1], has_entry('Quantity', 2))

	def test_purchasable(self):
		util = purchasable.PurchasableUtilityVocabulary(None)
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

	def test_priceable(self):
		pp = priceable.create_priceable(u'iid_3', 1)
		ext = to_external_object(pp)
		assert_that(ext, has_key('MimeType'))
		assert_that(ext, has_entry('NTIID', u'iid_3'))
		assert_that(ext, has_entry('Quantity', 1))
		assert_that(ext, has_entry('Class', u'Priceable'))

	def test_priced_item(self):
		pp = pricing.create_priced_item(ntiid=u'iid_3', purchase_price=100, purchase_fee=2)
		ext = to_external_object(pp)
		assert_that(ext, has_key('MimeType'))
		assert_that(ext, is_not(has_key('PurchaseFee')))
		assert_that(ext, is_not(has_key('NonDiscountedPrice')))
		assert_that(ext, has_entry('Provider', u'PRMIA'))
		assert_that(ext, has_entry('PurchasePrice', 100))
		assert_that(ext, has_entry('Class', u'PricedItem'))

		pp = pricing.create_priced_item(ntiid=u'iid_3', purchase_price=200,
										purchase_fee=30, non_discounted_price=220,
										quantity=10)
		ext = to_external_object(pp)
		assert_that(ext, is_not(has_key('PurchaseFee')))
		assert_that(ext, has_entry('NonDiscountedPrice', 220))
		assert_that(ext, has_entry('PurchasePrice', 200))
		assert_that(ext, has_entry('Quantity', 10))

	def test_fill_in_lib(self):
		pe = purchasable.create_purchasable(ntiid='tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.cosmetology',
									  		provider='MLC',
									  		amount=100)
		ext = to_external_object(pe)
		assert_that(ext, has_entry('Title', u'COSMETOLOGY'))
		assert_that(ext, has_entry('Description', u'COSMETOLOGY'))
