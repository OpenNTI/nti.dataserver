#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import greater_than
from nti.coremetadata.interfaces import IContextLastSeenContainer
does_not = is_not

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.users import User

from nti.externalization.interfaces import StandardExternalFields

TOTAL = StandardExternalFields.TOTAL


class TestIndexViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_rebuild_entity_catalog(self):
        res = self.testapp.post('/dataserver2/@@RebuildEntityCatalog',
                                status=200)
        assert_that(res.json_body,
                    has_entry(TOTAL, is_(greater_than(1))))

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_rebuild_context_lastseen_catalog(self):
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(username='ichigo')
            container = IContextLastSeenContainer(user)
            # pylint: disable=too-many-function-args
            container.append('ntiid_1', 1)
            container.append('ntiid_2', 1)
            container.append('ntiid_3', 1)

        res = self.testapp.post('/dataserver2/@@RebuildContextLastSeenCatalog',
                                status=200)
        assert_that(res.json_body,
                    has_entry(TOTAL, is_(greater_than(2))))
