#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

import unittest

from zope import interface

from zope.security.interfaces import IPrincipal

from nti.coremetadata.interfaces import system_user

from nti.messaging.interfaces import IMessage
from nti.messaging.interfaces import ISystemMessage
from nti.messaging.interfaces import IReceivedMessage
from nti.messaging.interfaces import IPeerToPeerMessage

from nti.messaging.model import Message
from nti.messaging.model import SystemMessage
from nti.messaging.model import ReceivedMessage
from nti.messaging.model import PeerToPeerMessage

from nti.messaging.tests import SharedConfiguringTestLayer


@interface.implementer(IPrincipal)
class MockPrincipal(object):

    title = description = u''

    def __init__(self, pid):
        self.id = pid


class TestModel(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_interface(self):
        message = Message(body=[u'bleach'],
                          To=[MockPrincipal('azien@bleach.org')],
                          From=MockPrincipal('ichigo@bleach.org'),
                          Subject=u'Bankai')
        assert_that(message, validly_provides(IMessage))
        assert_that(message, verifiably_provides(IMessage))

        message = SystemMessage(body=[u'bleach'],
                                To=[MockPrincipal('azien@bleach.org')],
                                From=system_user,
                                Subject=u'Bankai')
        assert_that(message, validly_provides(ISystemMessage))
        assert_that(message, verifiably_provides(ISystemMessage))

        message = PeerToPeerMessage(body=[u'bleach'],
                                    To=[MockPrincipal('azien@bleach.org')],
                                    From=MockPrincipal('ichigo@bleach.org'),
                                    Subject=u'Bankai')
        assert_that(message, validly_provides(IPeerToPeerMessage))
        assert_that(message, verifiably_provides(IPeerToPeerMessage))

        message = ReceivedMessage(Message=message)
        assert_that(message, validly_provides(IReceivedMessage))
        assert_that(message, verifiably_provides(IReceivedMessage))
