#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from zope.securitypolicy.rolepermission import AnnotationRolePermissionManager

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import ROLE_COMMUNITY_ADMIN_NAME
from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.interfaces import ICommunityPrincipalRoleManager
from nti.dataserver.interfaces import ICommunityRolePermissionManager
from nti.dataserver.interfaces import ISiteCommunity


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

    def __init__(self, context):
        super(PersistentCommunityRolePermissionManager, self).__init__(context)
        # We must call this here so that permissions are updated if the state changes
        self.initialize()

    def initialize(self):
        # Initialize with perms for our community admins
        for permission in (nauth.ACT_READ,
                           nauth.ACT_CREATE,
                           nauth.ACT_DELETE,
                           nauth.ACT_SEARCH,
                           nauth.ACT_LIST,
                           nauth.ACT_UPDATE):
            self.grantPermissionToRole(permission.id, ROLE_COMMUNITY_ADMIN_NAME)
            # If this isn't a site community we want to explicitly deny site admins
            if not ISiteCommunity.providedBy(self._context):
                self.denyPermissionToRole(permission.id, ROLE_SITE_ADMIN_NAME)
            else:
                self.grantPermissionToRole(permission.id, ROLE_SITE_ADMIN_NAME)

