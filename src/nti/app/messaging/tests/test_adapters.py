#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import same_instance

import unittest

from zope.security.interfaces import IPrincipal

from nti.dataserver.users import User

from nti.messaging.interfaces import IMailbox

from nti.messaging.model import PeerToPeerMessage

from nti.app.messaging.tests import SharedConfiguringTestLayer

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


class TestAdaptees(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_received_message_from_message(self):
        with mock_dataserver.mock_db_trans(self.ds):
            sender = User.create_user(dataserver=self.ds, username='ichigo')
            recipient = User.create_user(dataserver=self.ds, username='azien')
            message = PeerToPeerMessage(Date=1484598451,
                                        From=IPrincipal(sender),
                                        To=[IPrincipal(recipient)],
                                        Subject="keys",
                                        body='Piano')
    
            IMailbox(sender).send(message)
            mailbox = IMailbox(recipient)
            assert_that(mailbox.Received[message.__name__].Message,
                        is_(same_instance(message)))
