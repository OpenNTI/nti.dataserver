#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import zc.intid as zc_intid
from zope import component

from nti.dataserver import users

from nti.externalization import integer_strings

from ... import purchase_attempt
from ... import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from ...tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, none)

class TestInvitations(ConfiguringTestBase):
	
	processor = 'stripe'

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = users.User.create_user( self.ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_register_invitation(self):
		user = self._create_user()
		c = users.Community.create_community(self.ds, username='Bankai')
		
		hist = store_interfaces.IPurchaseHistory(user, None)
		pa = purchase_attempt.create_purchase_attempt(items='xyz', processor=self.processor)
		hist.add_purchase(pa)
	
		manager = component.getUtility(store_interfaces.IPaymentProcessor, name='stripe')
		
		invitation = manager.register_invitation(pa.id, user.username, (c,), 1)
		assert_that(invitation, is_not(none()))
		assert_that(invitation.capacity, is_(1))
		intid = integer_strings.from_external_string(invitation.code)
		obj = component.getUtility( zc_intid.IIntIds ).getObject( intid )
		assert_that(obj, is_(pa))
