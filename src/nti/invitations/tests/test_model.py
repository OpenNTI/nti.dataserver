#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import all_of
from hamcrest import has_entry
from hamcrest import assert_that

from nti.testing.matchers import verifiably_provides

import unittest

from nti.invitations.interfaces import IInvitation

from nti.invitations.model import Invitation

from nti.invitations.tests import SharedConfiguringTestLayer

from nti.externalization.tests import externalizes

class TestModel(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_valid_interface(self):
		assert_that(Invitation(), verifiably_provides(IInvitation))
	
	def test_external(self):
		invitation = Invitation(code='bleach',
								receiver='ichigo',
								inviter='aizen',
								accepted=True)
		assert_that(invitation, 
					externalizes(all_of(has_entry('code', 'bleach'),
								 has_entry('receiver', 'ichigo'),
								 has_entry('inviter', 'aizen'),
								 has_entry('accepted', is_(True)),
								 has_entry('expiryTime', is_(0)))))

	def test_misc(self):
		invitation = Invitation(code='bleach',
								receiver='ichigo',
								inviter='aizen',
								accepted=True)

		assert_that(invitation.is_expired(), is_(False))
		invitation.expiryTime = 10
		assert_that(invitation.is_expired(), is_(True))
		
		assert_that(invitation.is_email(), is_(False))
		invitation.receiver = 'ichigo@bleach.org'
		assert_that(invitation.is_email(), is_(True))
