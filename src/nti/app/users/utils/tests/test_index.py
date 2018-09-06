#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from nti.app.users.utils.index import get_context_lastseen_records
from nti.app.users.utils.index import get_context_lastseen_timestamp

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.coremetadata.interfaces import IContextLastSeenContainer

from nti.dataserver.tests import mock_dataserver


class TestIndex(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_get_lastseen_records(self):

        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(username=u'rukia',
                                     external_value={'email': u'rukia@bleach.com',
                                                     'realname': u'rukia kuchiki',
                                                     'alias': u'sode no shirayuki'})
            container = IContextLastSeenContainer(user)
            # pylint: disable=too-many-function-args
            container.append('1', 1)
            container.append('2', 2)

            records = get_context_lastseen_records()
            assert_that(records, has_length(0))

            records = get_context_lastseen_records('rukia')
            assert_that(records, has_length(2))

            records = get_context_lastseen_records('rukia', '1')
            assert_that(records, has_length(1))

            records = get_context_lastseen_records('aizen', '1')
            assert_that(records, has_length(0))

            ts = get_context_lastseen_timestamp(user, '2')
            assert_that(ts, is_(2))
