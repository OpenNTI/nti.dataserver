#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.app.users.utils import get_user_creation_site

from nti.dataserver.authorization import is_site_admin

from nti.dataserver.interfaces import ISiteAdminUtility
from nti.dataserver.interfaces import ISiteAdminManagerUtility

from nti.dataserver.users.interfaces import IUserUpdateUtility

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IUserUpdateUtility)
class UserUpdateUtility(object):
    """
    A default :class:`IUserUpdateUtility` that only allows updates on
    users created within this site.

    XXX: This should probably be a 'ThirdPartyUserUpdate` permission granted
    to NT admins on the ds folder and to site admin roles on their site.
    """

    def __init__(self, user):
        self.user = user

    def can_update_user(self, target_user):
        result = True
        if is_site_admin(self.user):
            site_admin_utility = component.getUtility(ISiteAdminUtility)
            result = site_admin_utility.can_administer_user(self.user,
                                                            target_user)
        return result


@interface.implementer(ISiteAdminUtility)
class SiteAdminUtility(object):
    """
    A default :class:`ISiteAdminUtility` that only allows site admins
    the ability to administer to users that were created in the current site, child site
    or have intersecting memberships.
    """

    def get_site_admin_membership_names(self, site_admin):
        memberships = site_admin.usernames_of_dynamic_memberships
        return memberships - {'Everyone'}

    def can_administer_user(self, site_admin, user, site_admin_membership_names=None):
        site_hierarchy = component.getUtility(ISiteAdminManagerUtility)
        user_creation_site = get_user_creation_site(user)
        admin_creation_site = get_user_creation_site(site_admin)
        if admin_creation_site is None:
            return False
        descendant_sites = site_hierarchy.get_descendant_sites(admin_creation_site)
        # Can administer if created in this site or any descendant
        result = user_creation_site in descendant_sites or user_creation_site is admin_creation_site
        if not result:
            logger.debug('Cannot administer user (site_admin=%s) (user=%s) (%s) (%s) (%s)',
                         site_admin, user, user_creation_site, admin_creation_site, descendant_sites)
            if not site_admin_membership_names:
                site_admin_membership_names = self.get_site_admin_membership_names(site_admin)
            user_membership_names = user.usernames_of_dynamic_memberships
            if user_membership_names:
                result = user_membership_names.intersection(site_admin_membership_names)
        return result


@interface.implementer(ISiteAdminUtility)
class GlobalSiteAdminUtility(object):
    """
    A :class:`ISiteAdminUtility` that allows site admins to administer anyone.
    This should be used with care.
    """

    def can_administer_user(self, unused_site_admin, unused_user):
        return True
