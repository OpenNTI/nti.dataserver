#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import is_
from hamcrest import is_not
from hamcrest import none

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.settings import Allow

from nti.dataserver.authorization import is_community_admin
from nti.dataserver.authorization import ROLE_COMMUNITY_ADMIN_NAME

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver.users import Community
from nti.dataserver.users import User

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class TestCommunityRoleManager(DataserverLayerTest):

    def test_site_role_manager(self):
        username = u'sheldon'
        user = User(username)
        community = Community(u'mycommunity')

        # Not a community admin by default
        assert_that(is_community_admin(user, community), is_(False))

        # Grant user admin access in community
        community_prm = IPrincipalRoleManager(community)
        assert_that(community_prm, is_not(none()))
        community_prm.assignRoleToPrincipal(ROLE_COMMUNITY_ADMIN_NAME,
                                            username)
        principals = community_prm.getPrincipalsForRole(ROLE_COMMUNITY_ADMIN_NAME)
        assert_that(principals, contains((username, Allow,)))
        assert_that(is_community_admin(user, community), is_(True))
