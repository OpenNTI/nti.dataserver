#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

import unittest

from zope import component

from zope.intid.interfaces import IIntIds

from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.chatserver.messageinfo import MessageInfo

from nti.chatserver.meeting import _Meeting as Meeting

from nti.dataserver.chat_transcripts import _IMeetingTranscriptStorage

from nti.dataserver.interfaces import ITranscript
from nti.dataserver.interfaces import ITranscriptSummary

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import mock_db_trans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.users.users import User

from nti.ntiids.oids import to_external_ntiid_oid


class TestAdapters(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDS
    def test_adapters(self):
        with mock_db_trans() as conn:
            user = User.create_user(username=u"sjohnson@nextthought.com")
            intids = component.getUtility(IIntIds)

            meeting = Meeting()
            meeting.containerId = u'the_container'
            conn.add(meeting)
            intids.register(meeting)
            meeting.id = meeting.ID = to_external_ntiid_oid(meeting)

            msg = MessageInfo()
            msg.creator = u"sjohnson@nextthought.com"
            msg.containerId = meeting.ID
            conn.add(msg)
            intids.register(msg)

            storage = IUserTranscriptStorage(user)
            # pylint: disable=too-many-function-args
            trx_storage = storage.add_message(meeting, msg)

            adapted = _IMeetingTranscriptStorage(msg, None)
            assert_that(adapted, is_not(none()))

            assert_that(adapted, is_(trx_storage))

            summary = ITranscriptSummary(msg, None)
            assert_that(summary, is_not(none()))
            
            transcript = ITranscript(msg, None)
            assert_that(transcript, is_not(none()))
