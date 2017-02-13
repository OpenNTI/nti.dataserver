#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

import unittest

from zope import interface

from zope.security.interfaces import IPrincipal

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IMessageContainer

from nti.messaging.storage import Mailbox
from nti.messaging.storage import MessageContainer
from nti.messaging.storage import ReceivedMessageContainer

from nti.messaging.model import Message
from nti.messaging.model import ReceivedMessage

from nti.messaging.tests import SharedConfiguringTestLayer


@interface.implementer(IPrincipal)
class MockPrincipal(object):

    title = description = u''

    def __init__(self, pid):
        self.id = pid


class TestStorage(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_interface(self):
        container = MessageContainer()
        assert_that(container, validly_provides(IMessageContainer))
        assert_that(container, verifiably_provides(IMessageContainer))

        container = Mailbox()
        assert_that(container, validly_provides(IMailbox))
        assert_that(container, verifiably_provides(IMailbox))

    def test_store(self):
        message = Message(body=[u'bleach'],
                          To=[MockPrincipal('azien@bleach.org')],
                          From=MockPrincipal('ichogo@bleach.org'),
                          Subject=u'Bankai')
        container = MessageContainer()
        container.append_message(message)
        assert_that(container, has_length(1))
        assert_that(message, has_property('id', is_not(none())))
        assert_that(message, has_property('__parent__', is_(container)))

        mid = message.id
        assert_that(container.get_message(mid), is_(message))

        message = ReceivedMessage(Message=message)
        container = ReceivedMessageContainer()
        container.add(message)
        assert_that(container, has_length(1))
        assert_that(message, has_property('id', is_not(none())))
        assert_that(message, has_property('__parent__', is_(container)))

        mid = message.id
        assert_that(container.get_message(mid), is_(message))
