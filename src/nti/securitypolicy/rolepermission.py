#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import Unset
from zope.securitypolicy.interfaces import IRolePermissionMap

from zope.securitypolicy.securitymap import SecurityMap

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IRolePermissionMap)
class PermissionGrantingRoleMap(SecurityMap):
    """
    A basic role permission map that grants a set
    of permissions to roles.
    """

    def __init__(self, grants=()):
        super(PermissionGrantingRoleMap, self).__init__()
        for role in grants or ():
            for perm in grants.get(role, ()):
                self.addCell(perm, role, Allow)

    getRolesForPermission = SecurityMap.getRow
    getPermissionsForRole = SecurityMap.getCol
    getRolesAndPermissions = SecurityMap.getAllCells

    def getSetting(self, permission_id, role_id, default=Unset):
        return self.queryCell(permission_id, role_id, default)
