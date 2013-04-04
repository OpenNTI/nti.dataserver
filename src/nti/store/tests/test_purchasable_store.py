#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

# from zope import component

# from nti.store import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import ConfiguringTestBase

# from hamcrest import (assert_that, is_, not_none)

class TestPurchasableStore(ConfiguringTestBase):

	@WithMockDSTrans
	def test_purchasable(self):
		pass
