#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver.users import User

from nti.store import purchase_order
from nti.store import purchase_attempt
from nti.store import purchase_history
from nti.store import interfaces as store_interfaces

from .. import nti_delete_purchase_attempt as nti_del

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_, is_not, none)

class TestDeletePurchaseAttempt(ConfiguringTestBase):

	processor = 'stripe'

	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
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
	def test_delete(self):
		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)

		pa_1 = self._create_purchase_attempt()
		hist.add_purchase(pa_1)
		assert_that(hist, has_length(1))

		pid = pa_1.id
		assert_that(pid, is_not(none()))

		# remove
		nti_del._delete_purchase(user.username, pid)

		pa = purchase_history.get_purchase_attempt(pid, user)
		assert_that(pa, is_(none()))
