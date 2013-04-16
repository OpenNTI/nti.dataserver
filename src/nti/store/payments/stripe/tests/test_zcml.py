#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import component

from nti.externalization.externalization import toExternalObject

from .. import interfaces as stripe_interfaces

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_not, none, has_key, has_entry)

class TestZcml(ConfiguringTestBase):

	def test_default_registrations(self):
		cap_name = 'NTI-TEST'
		sk = component.getUtility(stripe_interfaces.IStripeConnectKey, cap_name)
		assert_that(sk, is_not(none()))
		extobj = toExternalObject(sk)
		assert_that(extobj, is_not(has_key('PrivateKey')))
		assert_that(extobj, is_not(has_key('RefreshToken')))
		assert_that(extobj, has_entry('LiveMode', False))
		assert_that(extobj, has_entry('StripeUserID', 'NEXTTHOUGHT'))
		assert_that(extobj, has_entry('PublicKey', 'pk_test_LIpQyLD7p5FmspOs6pPW9gWG'))


