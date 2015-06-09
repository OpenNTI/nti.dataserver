#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import contains
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from zope.component import eventtesting

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitationAcceptedEvent

from nti.invitations.invitation import PersistentInvitation

from nti.testing.matchers import verifiably_provides

from nti.invitations.tests import SharedConfiguringTestLayer

class TestInvitation(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_valid_interface(self):
		assert_that(PersistentInvitation(), verifiably_provides(IInvitation))

	def test_accept_event(self):
		eventtesting.clearEvents()

		invite = PersistentInvitation()
		invite.accept(invite)

		assert_that(eventtesting.getEvents(IInvitationAcceptedEvent),
					contains(has_property('object', invite)))
