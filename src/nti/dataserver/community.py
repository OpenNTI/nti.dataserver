#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from zope.securitypolicy.rolepermission import AnnotationRolePermissionManager

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import ROLE_COMMUNITY_ADMIN_NAME

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

    def __nonzero__(self):
        return True
    __bool__ = __nonzero__

    def getRolesForPrincipal(self, principal_id):
        """
        Include site admin roles for Site Communities

        2/21/19
        Note that this allows child site admins to admin parent site communities
        and vice versa. We currently do not have a way to determine the creation site
        of a community, thus we are unable to only allow admins from that location.
        """
        roles = super(PersistentCommunityPrincipalRoleManager, self).getRolesForPrincipal(principal_id)
        if ISiteCommunity.providedBy(self._context):
            site = getSite()
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
