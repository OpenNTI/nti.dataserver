#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that

import fudge

from zope import component

from zope.intid.interfaces import IIntIds

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver


class TestViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_views(self):
        path = '/dataserver2/@@IntIdResolver/'
        self.testapp.get(path, status=422)

        path = '/dataserver2/@@IntIdResolver/xyz'
        self.testapp.get(path, status=422)

        with mock_dataserver.mock_db_trans(self.ds):
            user = self._get_user()
            intids = component.getUtility(IIntIds)
            uid = intids.getId(user)
        path = '/dataserver2/@@IntIdResolver/%s' % uid
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('Class', 'User'))

        path = '/dataserver2/@@IntIdInfo'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('size', is_not(none())))
        assert_that(res.json_body, has_entry('minKey', is_not(none())))
        assert_that(res.json_body, has_entry('maxKey', is_not(none())))
        assert_that(res.json_body, has_entry('attribute', is_not(none())))
        
    @WithSharedApplicationMockDS(users=True, testapp=True)
    @fudge.patch('nti.app.intids.views.IntIdResolverView.queryObject')
    def test_coverage(self, mock_qo):
        mock_qo.is_callable().raises(TypeError)
        path = '/dataserver2/@@IntIdResolver/442'
        self.testapp.get(path, status=422)
