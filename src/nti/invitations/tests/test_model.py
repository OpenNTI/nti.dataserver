#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

import unittest

from nti.externalization.tests import externalizes

from nti.invitations.interfaces import IUserInvitation
from nti.invitations.interfaces import DuplicateInvitationCodeError

from nti.invitations.model import UserInvitation
from nti.invitations.model import InvitationsContainer

from nti.invitations.tests import SharedConfiguringTestLayer


class TestModel(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_valid_interface(self):
        assert_that(UserInvitation(), verifiably_provides(IUserInvitation))

    def test_external(self):
        invitation = UserInvitation(code=u'bleach',
                                    receiver=u'ichigo',
                                    sender=u'aizen',
                                    accepted=True)
        assert_that(invitation,
                    externalizes(all_of(has_entry('code', 'bleach'),
                                        has_entry('receiver', 'ichigo'),
                                        has_entry('sender', 'aizen'),
                                        has_entry('accepted', is_(True)),
                                        has_entry('expiryTime', is_(0)))))

        assert_that(invitation, validly_provides(IUserInvitation))

    def test_misc(self):
        invitation = UserInvitation(code=u'bleach',
                                    receiver=u'ichigo',
                                    sender=u'aizen',
                                    accepted=True)

        assert_that(invitation.is_expired(), is_(False))
        invitation.expiryTime = 10
        assert_that(invitation.is_expired(), is_(True))

        assert_that(invitation.is_email(), is_(False))
        invitation.receiver = u'ichigo@bleach.org'
        assert_that(invitation.is_email(), is_(True))

    def test_container(self):
        invitation = UserInvitation(code=u'bleach',
                                    receiver=u'ichigo',
                                    sender=u'aizen',
                                    accepted=True)
        container = InvitationsContainer()
        container.add(invitation)
        assert_that(container, has_length(is_(1)))
        assert_that(invitation, has_property('code', is_not(none())))

        # Duplicate
        invitation = UserInvitation(code=u'bleach',
                                    receiver=u'ichigoxxx',
                                    sender=u'aizenxxx',
                                    accepted=False)
        with self.assertRaises(DuplicateInvitationCodeError):
            container.add(invitation)

        container.remove(invitation)
        assert_that(container, has_length(is_(0)))
