#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters for application-level events.

.. $Id$
"""

from __future__ import print_function, absolute_import, division

from zope.securitypolicy.settings import Allow

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.securitypolicy.interfaces import Deny
from zope.securitypolicy.interfaces import IRolePermissionMap

from zope.securitypolicy.rolepermission import AnnotationRolePermissionManager

from nti.dataserver.authorization import ACT_UPDATE
from nti.dataserver.authorization import ACT_CONTENT_EDIT
from nti.dataserver.authorization import ROLE_COMMUNITY_ADMIN_NAME
from nti.dataserver.authorization import ROLE_CONTENT_ADMIN_NAME

from nti.dataserver.contenttypes.forums.interfaces import IBoard
from nti.dataserver.contenttypes.forums.interfaces import ICommunityAdminRestrictedForum


@component.adapter(IBoard)
@interface.implementer(IRolePermissionMap)
class BoardRolePermissionManager(AnnotationRolePermissionManager):
    """
    A Zope `IRolePermissionMap` that denies any write access by global
    content admins to the boards
    """

    DENIED_PERMS = (ACT_UPDATE.id, ACT_CONTENT_EDIT.id)

    def __bool__(self):
        return True
    __nonzero__ = __bool__

    def getRolesForPermission(self, perm):
        result = super(BoardRolePermissionManager, self).getRolesForPermission(perm)
        if perm in self.DENIED_PERMS:
            super_roles = result
            result = []
            for role, setting in super_roles:
                if role != ROLE_CONTENT_ADMIN_NAME:
                    result.append((role, setting))
            result.append((ROLE_CONTENT_ADMIN_NAME, Deny))
        return result


@component.adapter(ICommunityAdminRestrictedForum)
@interface.implementer(IRolePermissionMap)
class CommunityAdminRestrictedForumRolePermissionManager(AnnotationRolePermissionManager):
    """
    A Zope `IRolePermissionMap` that grants all permissions
    to community admins in community admin restricted forums
    """

    def __bool__(self):
        return True
    __nonzero__ = __bool__

    def getRolesForPermission(self, perm):
        result = super(BoardRolePermissionManager, self).getRolesForPermission(perm)
        result.append((ROLE_COMMUNITY_ADMIN_NAME, Allow))
        return result
