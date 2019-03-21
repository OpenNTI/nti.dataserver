#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from zope.securitypolicy.rolepermission import AnnotationRolePermissionManager

from nti.app.users.utils import get_user_creation_site

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import ROLE_COMMUNITY_ADMIN_NAME

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

    def __nonzero__(self):
        return True
    __bool__ = __nonzero__

    def getRolesForPrincipal(self, principal_id):
        """
        Include site admin roles for Site Communities
        """
        roles = super(PersistentCommunityPrincipalRoleManager, self).getRolesForPrincipal(principal_id)
        site = get_user_creation_site(self._context)
        if site is not None:
            site_prm = IPrincipalRoleManager(site)
            site_roles = site_prm.getRolesForPrincipal(principal_id)
            for role in site_roles:
                roles.append(role)
        return roles


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
