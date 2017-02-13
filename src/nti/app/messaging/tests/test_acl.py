#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import not_
from hamcrest import assert_that

import unittest

from zope.security.interfaces import IPrincipal

from nti.dataserver import authorization as nauth

from nti.dataserver.users import User

from nti.messaging.model import PeerToPeerMessage

from nti.messaging.storage import Mailbox

from nti.app.messaging.tests import SharedConfiguringTestLayer

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.tests.test_authorization_acl import denies
from nti.dataserver.tests.test_authorization_acl import permits


class TestACLs(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_message_acls(self):
        username = 'aizen'
        username2 = 'ichigo'
        username3 = "abarai"
        adminUser = 'rukia@nextthought.com'

        User.create_user(username=username)
        User.create_user(username=username2)
        User.create_user(username=username3)
        User.create_user(username=adminUser)

        message = PeerToPeerMessage(From=IPrincipal(username),
                                    To=[IPrincipal(username2)],
                                    Subject='Bleach',
                                    body='Shikai')
        message.creator = username

        for action in (nauth.ACT_CREATE,
                       nauth.ACT_DELETE,
                       nauth.ACT_UPDATE,
                       nauth.ACT_READ):
            assert_that(message, permits(username, action))

        for action in (nauth.ACT_READ,):
            assert_that(message, permits(username2, action))

        for action in (nauth.ACT_CREATE, nauth.ACT_DELETE, nauth.ACT_UPDATE):
            assert_that(message, not_(permits(username2, action)))

        for action in (nauth.ACT_CREATE,
                       nauth.ACT_DELETE,
                       nauth.ACT_UPDATE,
                       nauth.ACT_READ):
            assert_that(message, not_(permits(username3, action)))

        for action in (nauth.ACT_CREATE,
                       nauth.ACT_DELETE,
                       nauth.ACT_UPDATE,
                       nauth.ACT_READ):
            assert_that(message, not_(permits(adminUser, action)))

    @WithMockDSTrans
    def test_mailbox_acls(self):
        username = 'user001'
        username2 = 'test001'

        User.create_user(username=username)
        User.create_user(username=username2)

        mailbox = Mailbox()
        mailbox.creator = username

        for action in (nauth.ACT_CREATE, nauth.ACT_UPDATE, nauth.ACT_READ):
            assert_that(mailbox, permits(username, action))

        for action in (nauth.ACT_DELETE,):
            assert_that(mailbox, not_(permits(username, action)))

        for action in (nauth.ACT_CREATE,
                       nauth.ACT_DELETE,
                       nauth.ACT_UPDATE,
                       nauth.ACT_READ):
            assert_that(mailbox, not_(permits(username2, action)))

        for action in (nauth.ACT_CREATE,
                       nauth.ACT_DELETE,
                       nauth.ACT_UPDATE,
                       nauth.ACT_READ):
            assert_that(mailbox, denies(username2, action))

        for action in (nauth.ACT_CREATE,
                       nauth.ACT_DELETE,
                       nauth.ACT_UPDATE,
                       nauth.ACT_READ):
            assert_that(mailbox, permits(nauth.ROLE_ADMIN.id, action))
