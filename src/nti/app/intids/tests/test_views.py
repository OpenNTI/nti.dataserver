#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_entry
from hamcrest import assert_that

from zope import component

from zope.intid.interfaces import IIntIds

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

import nti.dataserver.tests.mock_dataserver as mock_dataserver


class TestViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_intid_resolver(self):
        with mock_dataserver.mock_db_trans(self.ds):
            user = self._get_user()
            intids = component.getUtility(IIntIds)
            uid = intids.getId(user)
        path = '/dataserver2/@@IntIdResolver/%s' % uid
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('Class', 'User'))
