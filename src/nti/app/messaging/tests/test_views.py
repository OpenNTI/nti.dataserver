#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import assert_that
does_not = is_not

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

class TestApplicationInvitationUserViews(ApplicationLayerTest):

    def _link_with_rel(self, links, rel):
        for link in links:
            if link['rel'] == rel:
                return link
        return None

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def testGetHousingMailbox(self):
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user('ichigo')
            self._create_user('aizen')
            ichigo, aizen = 'ichigo', 'aizen'

        # users with a mailbox have the link to get it
        href = '/dataserver2/users/ichigo'
        resp = self.testapp.get(href, status=200, 
                                extra_environ=self._make_extra_environ(username=ichigo))
        resp = resp.json_body
        assert_that(resp, has_entry('Links', has_item(has_entry('rel', 'mailbox'))))

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
