#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder

from nti.app.users import VIEW_SITE_ADMINS

from nti.app.users.utils import set_user_creation_site
from nti.app.users.utils import get_user_creation_sitename

from nti.dataserver.authorization import is_site_admin

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.users import User

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS


class TestAuthorization(ApplicationLayerTest):
    """
    Test managing site administrators.
    """

    service_url = '/dataserver2/service/'

    def _get_site_admin_href(self, environ=None, require=True):
        service_res = self.testapp.get(self.service_url,
                                       extra_environ=environ)
        service_res = service_res.json_body
        workspaces = service_res['Items']
        admin_ws = None
        try:
            admin_ws = next(x for x in workspaces if x['Title'] == 'SiteAdmin')
        except StopIteration:
            pass
        if require:
            assert_that(admin_ws, not_none())
            return self.require_link_href_with_rel(admin_ws, VIEW_SITE_ADMINS)
        assert_that(admin_ws, none())

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_site_admin_management(self):
        regular_username = 'regular_user'
        other_site_username = 'other_site_user'
        alternative_site_name = 'other_site_name'
        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(username=other_site_username)
            set_user_creation_site(user, alternative_site_name)
            self._create_user(username=regular_username)

        admin_environ = self._make_extra_environ()
        regular_environ = self._make_extra_environ(user=regular_username)
        other_site_environ = self._make_extra_environ(user=other_site_username)
        for environ in (admin_environ, regular_environ, other_site_environ):
            environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'

        admin_site_href = self._get_site_admin_href(admin_environ)
        res = self.testapp.get(admin_site_href, extra_environ=admin_environ)
        res = res.json_body
        assert_that(res, has_entry('Items', has_length(0)))

        # Missing user/no user
        self.testapp.post(admin_site_href, extra_environ=admin_environ, status=422)
        self.testapp.post('%s/missing_user' % admin_site_href,
                          extra_environ=admin_environ,
                          status=404)

        self.testapp.delete(admin_site_href,
                            extra_environ=admin_environ,
                            status=422)
        self.testapp.delete('%s/missing_user' % admin_site_href,
                            extra_environ=admin_environ,
                            status=404)

        # Access
        self.testapp.post(admin_site_href,
                          extra_environ=regular_environ,
                          status=403)
        # Other user 401s since created in other site
        self.testapp.post(admin_site_href,
                          extra_environ=other_site_environ,
                          status=401)

        # Update
        self.testapp.post('%s/%s' % (admin_site_href, regular_username),
                          extra_environ=admin_environ)
        res = self.testapp.get(admin_site_href, extra_environ=admin_environ).json_body
        items = res['Items']
        assert_that(items, has_length(1))
        assert_that(items[0]['Username'], is_(regular_username))

        # Regular user
        admin_site_href = self._get_site_admin_href(regular_environ)
        res = self.testapp.get(admin_site_href, extra_environ=regular_environ).json_body
        items = res['Items']
        assert_that(items, has_length(1))
        assert_that(items[0]['Username'], is_(regular_username))

        # Invalid creation site
        # Can't test unless we had a legit user_creation_site
        #self.testapp.post('%s/%s' % (admin_site_href, other_site_username),
        #                  extra_environ=regular_environ,
        #                  status=422)

        self.testapp.post('%s/%s?force=True' % (admin_site_href, other_site_username),
                          extra_environ=regular_environ)

        # User has new creation site
        with mock_dataserver.mock_db_trans(self.ds,
                                           site_name='mathcounts.nextthought.com'):
            for username in (other_site_username, regular_username):
                user = User.get_user(username)
                user_site = get_user_creation_sitename(user)
                assert_that(user_site, is_('mathcounts.nextthought.com'))
                assert_that(is_site_admin(user), is_(True))

        res = self.testapp.get(admin_site_href, extra_environ=other_site_environ)
        res = res.json_body
        items = res['Items']
        assert_that(items, has_length(2))
        usernames = [x['Username'] for x in items]
        assert_that(usernames, contains_inanyorder(regular_username,
                                                   other_site_username))

        # Unwind
        self.testapp.delete('%s/%s' % (admin_site_href, other_site_username),
                            extra_environ=regular_environ)

        admin_site_href = self._get_site_admin_href(regular_environ)
        res = self.testapp.get(admin_site_href, extra_environ=regular_environ).json_body
        items = res['Items']
        assert_that(items, has_length(1))
        assert_that(items[0]['Username'], is_(regular_username))

        self.testapp.delete('%s/%s' % (admin_site_href, regular_username),
                            extra_environ=admin_environ)
        res = self.testapp.get(admin_site_href,
                               extra_environ=admin_environ).json_body
        items = res['Items']
        assert_that(items, has_length(0))

        # Access
        self.testapp.post(admin_site_href,
                          extra_environ=regular_environ,
                          status=403)
        self.testapp.post(admin_site_href,
                          extra_environ=other_site_environ,
                          status=403)
        self._get_site_admin_href(regular_environ, require=False)
        self._get_site_admin_href(other_site_environ, require=False)

        # Can re-add
        self.testapp.post('%s/%s' % (admin_site_href, regular_username),
                          extra_environ=admin_environ)
        res = self.testapp.get(admin_site_href, extra_environ=admin_environ)
        res = res.json_body
        items = res['Items']
        assert_that(items, has_length(1))
        assert_that(items[0]['Username'], is_(regular_username))

        # Adding a user with no site (dataserver2) fails.
        self.testapp.post('%s/%s' % (admin_site_href, regular_username),
                          status=422)

