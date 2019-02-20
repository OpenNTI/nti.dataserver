#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import is_
from hamcrest import is_not
from hamcrest import none

from zope import interface

from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.interfaces import IRolePermissionManager

from zope.securitypolicy.settings import Allow
from zope.securitypolicy.settings import Deny

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import ISiteCommunity

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver.users import Community
from nti.dataserver.users import User

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class TestCommunityPermissions(DataserverLayerTest):

    def test_community_permissions(self):
        username = u'sheldon'
        user = User(username)
        community = Community(u'mycommunity')

        # Not a community admin by default
        assert_that(community.is_admin(username), is_(False))

        community_prm = IPrincipalRoleManager(community)

        # Assert regular is granted no roles by community role manager
        roles = community_prm.getRolesForPrincipal(user)
        assert_that(roles, has_length(0))

        # Grant user admin access in community
        assert_that(community_prm, is_not(none()))
        community_prm.assignRoleToPrincipal(nauth.ROLE_COMMUNITY_ADMIN_NAME,
                                            username)
        principals = community_prm.getPrincipalsForRole(nauth.ROLE_COMMUNITY_ADMIN_NAME)
        assert_that(principals, contains((username, Allow,)))
        assert_that(community.is_admin(username), is_(True))

        # Assert community admin role has expected permissions
        community_rpm = IRolePermissionManager(community)
        permissions = community_rpm.getPermissionsForRole(nauth.ROLE_COMMUNITY_ADMIN_NAME)
        permissions = dict(permissions)
        assert_that(permissions, has_length(6))
        for permission in (nauth.ACT_READ,
                           nauth.ACT_CREATE,
                           nauth.ACT_DELETE,
                           nauth.ACT_SEARCH,
                           nauth.ACT_LIST,
                           nauth.ACT_UPDATE):
            assert_that(permissions, has_entry(permission.id, Allow))

        # Assert site admins cannot admin regular communities
        permissions = community_rpm.getPermissionsForRole(nauth.ROLE_SITE_ADMIN_NAME)
        permissions = dict(permissions)
        for permission in (nauth.ACT_READ,
                           nauth.ACT_CREATE,
                           nauth.ACT_DELETE,
                           nauth.ACT_SEARCH,
                           nauth.ACT_LIST,
                           nauth.ACT_UPDATE):
            assert_that(permissions, has_entry(permission.id, Deny))

        # Assert site admins can admin site communities
        interface.alsoProvides(community, ISiteCommunity)
        community_rpm = IRolePermissionManager(community)
        permissions = community_rpm.getPermissionsForRole(nauth.ROLE_SITE_ADMIN_NAME)
        permissions = dict(permissions)
        assert_that(permissions, has_length(6))
        for permission in (nauth.ACT_READ,
                           nauth.ACT_CREATE,
                           nauth.ACT_DELETE,
                           nauth.ACT_SEARCH,
                           nauth.ACT_LIST,
                           nauth.ACT_UPDATE):
            assert_that(permissions, has_entry(permission.id, Allow))
