#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import contains_inanyorder

import unittest

from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import Unset

from nti.securitypolicy.rolepermission import PermissionGrantingRoleMap


class TestPermissionGrantingRoleMap(unittest.TestCase):

    def setUp(self):
        self.rolemap = PermissionGrantingRoleMap({
            'role1': ('perm1',), 'role2': ('perm1', 'perm2',)
        })

    def test_permissions_for_role(self):
        permissions = self.rolemap.getPermissionsForRole('role1')
        assert_that(permissions, contains_inanyorder(('perm1', Allow)))

        permissions = self.rolemap.getPermissionsForRole('role2')
        assert_that(permissions,
                    contains_inanyorder(('perm1', Allow), ('perm2', Allow)))

    def test_get_roles_for_permission(self):
        roles = self.rolemap.getRolesForPermission('perm1')
        assert_that(roles,
                    contains_inanyorder(('role1', Allow), ('role2', Allow)))

        roles = self.rolemap.getRolesForPermission('perm2')
        assert_that(roles, contains_inanyorder(('role2', Allow)))

    def test_get_setting(self):
        assert_that(self.rolemap.getSetting('perm1', 'role2'), is_(Allow))
        assert_that(self.rolemap.getSetting('foo', 'role1'), is_(Unset))
        assert_that(self.rolemap.getSetting('perm1', 'bar'), is_(Unset))

    def test_roles_and_permissions(self):
        all_ = self.rolemap.getRolesAndPermissions()
        assert_that(all_, contains_inanyorder(('perm1', 'role1', Allow),
                                              ('perm1', 'role2', Allow),
                                              ('perm2', 'role2', Allow)))
