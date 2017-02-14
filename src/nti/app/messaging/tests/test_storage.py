#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import equal_to
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import same_instance

from zope.security.interfaces import IPrincipal

from nti.messaging.interfaces import IReceivedMessage

from nti.messaging.model import Message
from nti.messaging.model import ReceivedMessage

from nti.messaging.storage import MessageContainer
from nti.messaging.storage import ReceivedMessageContainer

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


class TestStorage(ApplicationLayerTest):

    @WithMockDSTrans
    def test_message_container(self):
        folder = MessageContainer()
        current_trx = mock_dataserver.current_transaction
        current_trx.add(folder)

        from_user = IPrincipal('user001')
        to_user_1 = IPrincipal('user002')
        to_user_2 = IPrincipal('user003')
        subject = 'No strings attached'

        message = Message(Date=1484598451,
                          From=from_user,
                          To=[to_user_1, to_user_2],
                          Subject=subject,
                          body='Piano')
        assert_that(message.__parent__, same_instance(None))
        assert_that(message.__name__, same_instance(None))

        result = folder.append_message(message)

        assert_that(result, same_instance(message))
        assert_that(result.__parent__, same_instance(folder))
        assert_that(message.__name__, not_none())

        message2 = Message(Date=1484598451,
                           From=from_user,
                           To=[to_user_1, to_user_2],
                           Subject=subject,
                           body='Piano')
        folder.append_message(message2)

        items = [x for x in folder.values()]
        assert_that(items, has_length(2))

        folder.delete_message(message)

        items = [x for x in folder.values()]
        assert_that(items, has_length(1))
        assert_that(message.__name__ in folder, is_(False))
        assert_that(message2.__name__ in folder, is_(True))
        assert_that(message.__name__, is_not(equal_to(message2.__name__)))

    @WithMockDSTrans
    def test_received_message_container(self):
        folder = ReceivedMessageContainer()
        current_trx = mock_dataserver.current_transaction
        current_trx.add(folder)

        from_user = IPrincipal('user001')
        to_user_1 = IPrincipal('user002')
        to_user_2 = IPrincipal('user003')
        subject = 'No strings attached'

        message = Message(Date=1484598451,
                          From=from_user,
                          To=[to_user_1, to_user_2],
                          Subject=subject,
                          body='Piano')
        message.__name__ = '1'
        received_message = IReceivedMessage(message)
        assert_that(received_message.__parent__, same_instance(None))

        result = folder.append(received_message)

        assert_that(result, same_instance(received_message))
        assert_that(result.__parent__, same_instance(folder))

        message2 = Message(Date=1484598451,
                           From=from_user,
                           To=[to_user_1, to_user_2],
                           Subject=subject,
                           body='Piano')
        message2.__name__ = '2'
        received_message_2 = ReceivedMessage(ViewedDate=1484598451,
                                             ReplyDate=1484598452,
                                             ForwardDate=1484598453,
                                             Message=message2)
        folder.add(received_message_2)

        assert_that(folder, has_length(2))

        folder.remove(received_message)

        assert_that(folder, has_length(1))
        assert_that(received_message.__name__ in folder, is_(False))
        assert_that(received_message_2.__name__ in folder, is_(True))
