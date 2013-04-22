#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import stripe

from nti.dataserver.users import User

from .. import StripeException
from .. import interfaces as stripe_interfaces

from nti.store import purchase_order
from nti.store import purchase_attempt
from nti.store import interfaces as store_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, none)

class TestStripeAdapters(ConfiguringTestBase):

	processor = 'stripe'

	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_stripe_customer_adapter(self):
		user = self._create_user()
		adapted = stripe_interfaces.IStripeCustomer(user)
		assert_that(adapted, is_not(None))
		assert_that(adapted.customer_id, is_(None))

		adapted.Charges.add('ch_id')
		assert_that('ch_id' in adapted, is_(True))

		adapted.customer_id = 'xyz'
		assert_that(adapted.customer_id, is_('xyz'))

	def _create_purchase_attempt(self, item=u'xyz-book', quantity=None,
								 state=store_interfaces.PA_STATE_UNKNOWN,
								 description='my purchase'):
		pi = purchase_order.create_purchase_item(item, 1)
		po = purchase_order.create_purchase_order(pi, quantity=quantity)
		pa = purchase_attempt.create_purchase_attempt(po, processor=self.processor,
													  description=description,
													  state=state)
		return pa

	@WithMockDSTrans
	def test_stripe_purchase_adapter(self):
		pa = self._create_purchase_attempt()
		adapted = stripe_interfaces.IStripePurchaseAttempt(pa)
		adapted.charge_id = 'charge_id'
		adapted.token_id = 'token_id'
		assert_that(adapted.purchase, is_(pa))
		assert_that(adapted.charge_id, is_('charge_id'))
		assert_that(adapted.token_id, is_('token_id'))

	def test_stripe_error_adapters(self):
		e = stripe.CardError('my error', 'my param', 'my code')
		adapted = stripe_interfaces.IStripePurchaseError(e, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted.Type, is_('CardError'))
		assert_that(adapted.Message, is_('my error'))
		assert_that(adapted.Param, is_('my param'))
		assert_that(adapted.Code, is_('my code'))

		e = StripeException('my exception')
		adapted = stripe_interfaces.IStripePurchaseError(e, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted.Type, is_('Exception'))
		assert_that(adapted.Message, is_('my exception'))

		e = u'my error message'
		adapted = stripe_interfaces.IStripePurchaseError(e, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted.Type, is_('Error'))
		assert_that(adapted.Message, is_('my error message'))
