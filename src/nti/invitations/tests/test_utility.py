#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import verifiably_provides

import fudge
import unittest

from zope import interface

from zope.keyreference.interfaces import IKeyReference

from nti.invitations import utility
from nti.invitations import interfaces
from nti.invitations import invitation

from nti.invitations.tests import SharedConfiguringTestLayer

class TestUtility(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_valid_interface(self):
		assert_that(utility.PersistentInvitations(), 
					verifiably_provides(interfaces.IInvitations))

	@fudge.patch('nti.invitations.utility.get_invitation_code')
	def test_add_remove_invitation(self, mock_gic):
		mock_gic.is_callable().returns('xyx')
		invites = utility.PersistentInvitations()

		invite = invitation.PersistentInvitation()
		invite.code = 'my code'

		invites.registerInvitation(invite)
		assert_that(invite, has_property('code', 'my code'))

		assert_that(invites.getInvitationByCode('my code'), is_(invite))

		invite = invitation.PersistentInvitation()
		interface.alsoProvides(invite, IKeyReference)

		invites.registerInvitation(invite)
		assert_that(invite, has_property('code', is_not(none())))

		assert_that(invites.getInvitationByCode(invite.code), is_(invite))

		for x in invites.sublocations():
			assert_that(x, has_property('__parent__', invites))

		invites.removeInvitation(invite)
