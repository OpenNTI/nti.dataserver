#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
from hamcrest import is_
from hamcrest import has_item
from hamcrest import has_items
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS


class TestAuthorization(ApplicationLayerTest):
    """
    Test managing administrators.
    """

    service_url = '/dataserver2/service/'

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_admin_management(self):
        regular_username = 'regular_user'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=regular_username)
            initial_admin_username = self._get_user().username

        admin_environ = self._make_extra_environ()
        regular_environ = self._make_extra_environ(user=regular_username)
        for environ in (admin_environ, regular_environ):
            environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'

        admin_href = "/dataserver2/Admins"
        res = self.testapp.get(admin_href, extra_environ=admin_environ)
        res = res.json_body
        assert_that(res, has_entry('Items', has_length(1)))
        assert_that(res['Items'],
                    has_item(
                        has_entry('Username', is_(initial_admin_username)),
                    ))

        # Missing user/no user
        self.testapp.post(admin_href,
                          extra_environ=admin_environ, status=422)
        self.testapp.post('%s/missing_user' % admin_href,
                          extra_environ=admin_environ,
                          status=404)

        self.testapp.delete(admin_href,
                            extra_environ=admin_environ,
                            status=422)
        self.testapp.delete('%s/missing_user' % admin_href,
                            extra_environ=admin_environ,
                            status=404)

        # Access
        self.testapp.post(admin_href,
                          extra_environ=regular_environ,
                          status=403)

        # Update (regular_username is now a admin)
        self.testapp.post('%s/%s' % (admin_href, regular_username),
                          extra_environ=admin_environ)
        res = self.testapp.get(admin_href,
                               extra_environ=admin_environ).json_body
        items = res['Items']
        assert_that(items, has_length(2))
        assert_that(res['Items'],
                    has_items(
                        has_entry('Username', is_(regular_username)),
                        has_entry('Username', is_(initial_admin_username)),
                    ))

        # Regular user
        params = {'sortOn': 'createdTime', 'searchTerm': 'regu'}
        res = self.testapp.get(admin_href, params=params,
                               extra_environ=regular_environ).json_body
        items = res['Items']
        assert_that(items, has_length(1))
        assert_that(items[0]['Username'], is_(regular_username))

        # Unwind
        self.testapp.delete('%s/%s' % (admin_href, regular_username),
                            extra_environ=admin_environ)
        res = self.testapp.get(admin_href,
                               extra_environ=admin_environ).json_body
        items = res['Items']
        assert_that(items, has_length(1))

        # Access
        self.testapp.post(admin_href,
                          extra_environ=regular_environ,
                          status=403)

        # Can re-add
        self.testapp.post('%s/%s' % (admin_href, regular_username),
                          extra_environ=admin_environ)
        res = self.testapp.get(admin_href, extra_environ=admin_environ)
        res = res.json_body
        items = res['Items']
        assert_that(items, has_length(2))
        assert_that(res['Items'],
                    has_items(
                        has_entry('Username', is_(regular_username)),
                        has_entry('Username', is_(initial_admin_username)),
                    ))
