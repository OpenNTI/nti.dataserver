#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import IPrincipalPermissionMap

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from zope.securitypolicy.rolepermission import AnnotationRolePermissionManager

from zope.securitypolicy.settings import Unset

from nti.app.users.utils import get_site_admins
from nti.app.users.utils import get_entity_creation_site

from nti.coremetadata.interfaces import IUser

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_MANAGE_PROFILE 

from nti.dataserver.authorization import ROLE_COMMUNITY_ADMIN_NAME

from nti.dataserver.authorization import is_site_admin

from nti.dataserver.interfaces import ISiteAdminUtility
from nti.dataserver.interfaces import ICommunityPrincipalRoleManager
from nti.dataserver.interfaces import ICommunityRolePermissionManager

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IUserProfile

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
        Site admins for this community get de-facto community admin roles.
        """
        roles = super(PersistentCommunityPrincipalRoleManager, self).getRolesForPrincipal(principal_id)
        site = get_entity_creation_site(self._context)
        if site is not None:
            user = User.get_user(principal_id)
            if user is not None and is_site_admin(user, site):
                roles.append((ROLE_COMMUNITY_ADMIN_NAME, Allow))
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
                           nauth.ACT_PIN,
                           nauth.ACT_LIST,
                           nauth.ACT_UPDATE):
            self.grantPermissionToRole(permission.id, ROLE_COMMUNITY_ADMIN_NAME)


@component.adapter(IUserProfile)
@interface.implementer(IPrincipalPermissionMap)
class UserProfilePrincipalPermissionMap(object):
    """
    Ensure our site admins have access to manage user profiles.
    """

    SITE_ADMIN_PERM_IDS = (ACT_READ.id, ACT_MANAGE_PROFILE.id)

    def __init__(self, context):
        self.context = context
        self._user = IUser(context)

    @Lazy
    def siteAdminUtility(self):
        return component.getUtility(ISiteAdminUtility)

    def _can_admin(self, site_admin):
        return self.siteAdminUtility.can_administer_user(site_admin,
                                                         self._user)

    @Lazy
    def _effectiveAdminsForUser(self):
        return [site_admin.username for site_admin in get_site_admins()
                if self._can_admin(site_admin)]

    def getPrincipalsForPermission(self, perm):
        result = []
        if perm in self.SITE_ADMIN_PERM_IDS:
            for principal_id in self._effectiveAdminsForUser:
                result.append((principal_id, Allow))
        return result

    def getPermissionsForPrincipal(self, principal_id):
        if principal_id in self._effectiveAdminsForUser:
            return [(perm, Allow) for perm in self.SITE_ADMIN_PERM_IDS]

        return []

    def getSetting(self, permission_id, principal_id, default=Unset):
        if permission_id in self.SITE_ADMIN_PERM_IDS:
            if principal_id in self._effectiveAdminsForUser:
                return Allow

        return default

    def getPrincipalsAndPermissions(self):
        result = []
        for principal_id in self._effectiveAdminsForUser:
            for perm in self.SITE_ADMIN_PERM_IDS:
                result.append((principal_id, perm, Allow))

        return result
