#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import verifiably_provides

import unittest

from nti.invitations.interfaces import IInvitation

from nti.invitations.model import Invitation
from nti.invitations.model import InvitationsContainer

from nti.invitations.tests import SharedConfiguringTestLayer

from nti.externalization.tests import externalizes


class TestModel(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_valid_interface(self):
        assert_that(Invitation(), verifiably_provides(IInvitation))

    def test_external(self):
        invitation = Invitation(code=u'bleach',
                                receiver=u'ichigo',
                                sender=u'aizen',
                                accepted=True)
        assert_that(invitation,
                    externalizes(all_of(has_entry('code', 'bleach'),
                                        has_entry('receiver', 'ichigo'),
                                        has_entry('sender', 'aizen'),
                                        has_entry('accepted', is_(True)),
                                        has_entry('expiryTime', is_(0)))))

    def test_misc(self):
        invitation = Invitation(code=u'bleach',
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
        invitation = Invitation(code=u'bleach',
                                receiver=u'ichigo',
                                sender=u'aizen',
                                accepted=True)
        container = InvitationsContainer()
        container.add(invitation)
        assert_that(container, has_length(is_(1)))
        assert_that(invitation, has_property('code', is_not(none())))

        container.remove(invitation)
        assert_that(container, has_length(is_(0)))
