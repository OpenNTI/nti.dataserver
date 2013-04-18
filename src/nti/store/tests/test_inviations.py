#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver.users import User

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
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_create_invitation(self):
		user = self._create_user()

		hist = store_interfaces.IPurchaseHistory(user, None)
		purchase = purchase_attempt.create_purchase_attempt(items='xyz', processor=self.processor, quantity=1)
		hist.add_purchase(purchase)

		invitation = invitations.create_store_purchase_invitation(purchase)
		assert_that(invitation, is_(not_none()))
		assert_that(invitation.capacity, is_(1))
		assert_that(invitation.creator, is_(user))
		assert_that(invitation.code, is_(not_none()))

		user2 = self._create_user(username='nt2@nti.com')
		invitation.accept(user2)

		user3 = self._create_user(username='nt3@nti.com')
		with assert_raises(invitations.InvitationCapacityExceeded):
			invitation.accept(user3)
