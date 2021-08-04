#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from hamcrest import assert_that
from hamcrest import is_

from zope import component

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.site.hostpolicy import create_site

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.authorization import ROLE_ADMIN_NAME
from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.interfaces import ISiteAdminUtility

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.dataserver.users.common import set_user_creation_site


class TestAdminUtility(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=("nti.admin",
                                        "site.admin",
                                        "no.creation.site.admin",
                                        "diff.site.admin",
                                        "not.site.admin"))
    def test_can_admin(self):
        with mock_ds.mock_db_trans(self.ds,
                                   site_name="alpha.nextthought.com"):
            # NTI admins can always admin all users
            admin = self._get_user('nti.admin')
            self._assign_role(ROLE_ADMIN_NAME, admin.username)

            # A user that can administer "not.site.admin"
            site_admin = self._get_user('site.admin')
            site = getSite()
            site_name = site.__name__
            set_user_creation_site(site_admin, site_name)
            prm = IPrincipalRoleManager(site)
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, site_admin.username)

            # A site admin in the same site as user, but with no creation site
            # set, should not be able to admin
            no_creation_site_admin = self._get_user('no.creation.site.admin')
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, no_creation_site_admin.username)

            # A user that cannot administer "not.site.admin" (site admin for
            # another site)
            # Use a created site so we can ensure the truthiness of the site
            # itself evaluates to False, as this previously caused issues.
            site = create_site('diff.site')
            prm = IPrincipalRoleManager(site)
            diff_site_admin = self._get_user('diff.site.admin')
            set_user_creation_site(diff_site_admin, 'diff.site')
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, diff_site_admin.username)

            # User to check against
            not_admin = self._get_user('not.site.admin')
            set_user_creation_site(not_admin, site_name)

            site_admin_util = component.getUtility(ISiteAdminUtility)

            assert_that(bool(site_admin_util.can_administer_user(admin, not_admin)),
                        is_(True))
            assert_that(bool(site_admin_util.can_administer_user(site_admin, not_admin)),
                        is_(True))
            assert_that(bool(site_admin_util.can_administer_user(no_creation_site_admin, not_admin)),
                        is_(False))
            assert_that(bool(site_admin_util.can_administer_user(diff_site_admin, not_admin)),
                        is_(False))
