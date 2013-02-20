#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from nti.dataserver.users import User
from nti.dataserver.users import Community

from .. import invitations
from .. import purchase_attempt
from .. import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from nose.tools import assert_raises
from hamcrest import (assert_that, is_, not_none)

class TestInvitations(ConfiguringTestBase):
	
	processor = 'stripe'

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user( self.ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_create_invitation(self):
		user = self._create_user()
		c = Community.create_community(self.ds, username='Bankai')
		
		hist = store_interfaces.IPurchaseHistory(user, None)
		pa = purchase_attempt.create_purchase_attempt(items='xyz', processor=self.processor)
		hist.add_purchase(pa)
	
		invitation = invitations.create_store_invitation(pa.id, user.username, (c,), 1)
		assert_that(invitation, is_(not_none()))
		assert_that(invitation.capacity, is_(1))
		assert_that(invitation.code, is_(not_none()))
		assert_that(invitation.creator, is_(user.username))
		
		assert_that(invitation.consume(), is_(True))
		assert_that(invitation.consume(), is_(False))
		
		user2 = self._create_user(username='nt2@nti.com')
		with assert_raises(invitations.InvitationCapacityExceeded):
			invitation.accept(user2)

	
