#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_property
from hamcrest import is_not
from hamcrest import none

from zope import component
from zope import interface

from zope.keyreference.interfaces import IKeyReference

from zope.intid import IIntIds

from nti.invitations import utility
from nti.invitations import interfaces
from nti.invitations import invitation

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.testing.matchers import verifiably_provides

class TestUtility(DataserverLayerTest):

	def test_valid_interface(self):
		assert_that(utility.PersistentInvitations(), 
					verifiably_provides(interfaces.IInvitations))

	@WithMockDSTrans
	def test_add_remove_invitation(self):

		invites = utility.PersistentInvitations()
		ids = component.getUtility(IIntIds)
		ids.register(invites)
		ids._p_jar.add(invites)

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
