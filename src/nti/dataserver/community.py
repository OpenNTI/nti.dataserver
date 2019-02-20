#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from zope.securitypolicy.rolepermission import AnnotationRolePermissionManager

from nti.dataserver.authorization import ROLE_COMMUNITY_ADMIN_NAME

from nti.dataserver.interfaces import ALL_PERMISSIONS
from nti.dataserver.interfaces import ICommunityPrincipalRoleManager
from nti.dataserver.interfaces import ICommunityRolePermissionManager

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICommunityPrincipalRoleManager)
class PersistentCommunityPrincipalRoleManager(AnnotationPrincipalRoleManager):
    """
    An implementation of :class:`ICommunityRoleManager` that will return
    persistently stored principals/roles.
    """


@interface.implementer(ICommunityRolePermissionManager)
class PersistentCommunityRolePermissionManager(AnnotationRolePermissionManager):

    def initialize(self):
        if not self.map or not self.map._byrow:  # pylint: disable=protected-access
            # Initialize with perms for our community admins
            self.grantPermissionToRole(ALL_PERMISSIONS, ROLE_COMMUNITY_ADMIN_NAME)
