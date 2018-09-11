#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from zope import component

from zope.intid.interfaces import IIntIds

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.webtest import TestApp

from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.chatserver.messageinfo import MessageInfo

from nti.chatserver.meeting import _Meeting as Meeting

from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.tests.mock_dataserver import mock_db_trans

from nti.ntiids.oids import to_external_ntiid_oid


class TestTranscript(ApplicationLayerTest):

    @WithSharedApplicationMockDS
    def test_transcript(self):
        with mock_db_trans() as conn:
            ichigo = self._create_user(u"ichigo")
            self._create_user(u"rukia")
            intids = component.getUtility(IIntIds)

            # sample meeting
            meeting = Meeting()
            meeting.creator = u'ichigo'
            meeting.containerId = u'tag:nextthought.com,2011-10:Root'
            conn.add(meeting)
            intids.register(meeting)
            meeting.add_occupant_name("rukia", False)
            meeting.id = meeting.ID = to_external_ntiid_oid(meeting)

            # index
            doc_id = intids.getId(meeting)
            get_metadata_catalog().index_doc(doc_id, meeting)

            # sample message
            msg = MessageInfo()
            msg.creator = "ichigo"
            msg.containerId = meeting.ID
            msg.setSharedWithUsernames(("rukia", 'ichigo'))
            conn.add(msg)
            intids.register(msg)

            # index
            doc_id = intids.getId(msg)
            get_metadata_catalog().index_doc(doc_id, msg)

            # create storage
            storage = IUserTranscriptStorage(ichigo)
            # pylint: disable=too-many-function-args
            storage.add_message(meeting, msg)

        # pylint: disable=no-member
        testapp = TestApp(self.app)

        path = '/dataserver2/users/ichigo/@@transcripts'
        params = {'containeId': 'tag:nextthought.com,2011-10:Root',
                  'recursive': True,
                  'sortOn': 'containerId',
                  'contributor': 'rukia'}
        res = testapp.get(path, params=params,
                          extra_environ=self._make_extra_environ(user="ichigo"),
                          status=200)
        assert_that(res.json_body,
                    has_entry('Items',
                              has_length(1)))

        testapp.get(path, params=params,
                    extra_environ=self._make_extra_environ(user="rukia"),
                    status=403)
