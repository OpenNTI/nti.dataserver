#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import contains
from hamcrest import assert_that
from hamcrest import has_property

from nti.appserver.invitations.interfaces import IInvitation
from nti.appserver.invitations.interfaces import IInvitationAcceptedEvent

from nti.appserver.invitations.invitation import PersistentInvitation

from zope.component import eventtesting

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.testing.matchers import verifiably_provides

class TestInvitation(DataserverLayerTest):
	
	def test_valid_interface(self):
		assert_that(PersistentInvitation(), verifiably_provides( IInvitation ) )

	def test_accept_event(self):
		eventtesting.clearEvents()

		invite = PersistentInvitation()
		invite.accept( invite )

		assert_that( eventtesting.getEvents( IInvitationAcceptedEvent ),
					 contains( has_property( 'object', invite ) ) )
