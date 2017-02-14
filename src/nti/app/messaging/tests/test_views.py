#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import same_instance
from hamcrest import has_properties
does_not = is_not

from zope.security.interfaces import IPrincipal

from nti.dataserver.users import User

from nti.messaging.interfaces import IMailbox

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver


class TestMessagingViews(ApplicationLayerTest):

    def _link_with_rel(self, links, rel):
        for link in links:
            if link['rel'] == rel:
                return link
        return None

    def _get_sent_messages(self, username):
        user = User.get_user(username)
        mailbox = IMailbox(user)
        return list(mailbox.Sent.values())

    def _get_received_messages(self, username):
        user = User.get_user(username)
        mailbox = IMailbox(user)
        return list(mailbox.Received.values())

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_get_mailbox(self):
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user('ichigo')
            self._create_user('aizen')
            ichigo, aizen = 'ichigo', 'aizen'

        # users with a mailbox have the link to get it
        href = '/dataserver2/users/ichigo'
        resp = self.testapp.get(href, status=200,
                                extra_environ=self._make_extra_environ(username=ichigo))
        resp = resp.json_body
        assert_that(resp,
                    has_entry('Links',
                              has_item(has_entry('rel', 'mailbox'))))

        # fetching the link works for the owner
        href = self._link_with_rel(resp['Links'], 'mailbox')['href']
        resp = self.testapp.get(href, status=200,
                                extra_environ=self._make_extra_environ(username=ichigo))
        resp = resp.json_body
        assert_that(resp,
                    has_entry('MimeType', 'application/vnd.nextthought.messaging.mailbox'))

        # but you can't fetch someone elses
        self.testapp.get(href, status=403,
                         extra_environ=self._make_extra_environ(username=aizen))

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_new_message(self):
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user('ichigo')
            self._create_user('aizen')

        ext_obj = {
            "Subject": "How are you",
            "From": "ichigo",
            "To": ["aizen"],
            "body": "how are you",
            "MimeType": "application/vnd.nextthought.messaging.peertopeermessage"
        }

        # can't post new messgon on someone else's IMailbox
        href = '/dataserver2/users/ichigo/mailbox'
        self.testapp.post_json(href, ext_obj,
                               status=403,
                               extra_environ=self._make_extra_environ(username='aizen'))

        # post new message on the creator's IMailbox
        res = self.testapp.post_json(href, ext_obj,
                                     status=201,
                                     extra_environ=self._make_extra_environ(username="ichigo"))

        assert_that(res.json_body,
                    has_entry('Links',
                              has_item(has_entry('rel', 'reply'))))

        assert_that(res.json_body,
                    has_entries(u'MimeType', u'application/vnd.nextthought.messaging.conversation',
                                u'MostRecentMessage', is_not(none()),
                                u'UnOpenedCount', 1,
                                u'Participants', [u'aizen', u'ichigo']))

        # verify the message is in the sender's IMailbox and the
        # receiver's IMailbox
        with mock_dataserver.mock_db_trans(self.ds):
            sent_messages = self._get_sent_messages('ichigo')
            assert_that(sent_messages, has_length(1))
            assert_that(sent_messages[0],
                        has_properties({'Subject': 'How are you',
                                        'From': IPrincipal('ichigo'),
                                        'To': (IPrincipal('aizen'),),
                                        'body': 'how are you'}))

            received_messages = self._get_received_messages('aizen')
            assert_that(received_messages, has_length(1))
            assert_that(received_messages[0].Message,
                        same_instance(sent_messages[0]))
