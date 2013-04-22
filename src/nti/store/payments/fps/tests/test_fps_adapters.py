#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from .... import purchase_order
from .... import purchase_attempt
from .. import interfaces as fps_interfaces

from . import ConfiguringTestBase

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from hamcrest import (assert_that, is_)

class TestFPSAdapters(ConfiguringTestBase):

	processor = 'fps'

	def _create_purchase_attempt(self, item=u'xyz-book', description=None):
		pi = purchase_order.create_purchase_item(item, 1)
		po = purchase_order.create_purchase_order(pi)
		pa = purchase_attempt.create_purchase_attempt(po, processor=self.processor,
													  description=description)
		return pa


	@WithMockDSTrans
	def test_stripe_purchase_adapter(self):
		pa = self._create_purchase_attempt()
		adapted = fps_interfaces.IFPSPurchaseAttempt(pa)
		adapted.TokenID = 'token_id'
		adapted.TransactionID = 'trxid'
		adapted.CallerReference = 'caller'
		assert_that(adapted.caller_reference, is_('caller'))
		assert_that(adapted.transaction_id, is_('trxid'))
		assert_that(adapted.token_id, is_('token_id'))
