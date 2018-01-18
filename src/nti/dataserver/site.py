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
from zope import deferredimport

from zope.cachedescriptors.property import Lazy

from zope.securitypolicy.interfaces import Unset

from zope.securitypolicy.principalrole import PrincipalRoleManager
from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from nti.dataserver.interfaces import ISiteRoleManager

from nti.externalization.persistence import NoPickle

logger = __import__('logging').getLogger(__name__)


@NoPickle
@interface.implementer(ISiteRoleManager)
class SiteRoleManagerUtility(PrincipalRoleManager):
    """
    Instances of this class should be registered as utilities inside a site.
    """
SiteRoleManager = SiteRoleManagerUtility


@interface.implementer(ISiteRoleManager)
class PersistentSiteRoleManager(AnnotationPrincipalRoleManager):
    """
    An implementation of :class:`ISiteRoleManager` that will return
    persistently store principals/roles as well as falling back to
    the :class:`ISiteRoleManagerUtility`.
    """

    def __nonzero__(self):
        # Always want to return data since we may be pulling from another
        # role manager.
        return True

    @Lazy
    def _site_role_manager_utility(self):
        return component.queryUtility(ISiteRoleManager)

    def getSetting(self, role_id, principal_id, default=Unset):
        """
        Return the setting for this principal, role combination
        """
        result = super(PersistentSiteRoleManager, self).getSetting(role_id,
                                                                   principal_id,
                                                                   None)
        if result is None:
            util = self._site_role_manager_utility
            if util is not None:
                result = util.getSetting(role_id, principal_id, default=default)
        return result

    def _accumulate(self, func_name, *args):
        """
        Call the given `func_name` on ourselves, adding to the result found in
        the utility. Note, we do not try to dedupe here for performance.
        """
        super_func = getattr(super(PersistentSiteRoleManager, self), func_name)
        result = super_func(*args)
        result = result or []
        util = self._site_role_manager_utility
        if util is not None:
            util_func = getattr(util, func_name)
            util_result = util_func(*args)
            result.extend(util_result or ())
        return result

    def getPrincipalsForRole(self, role_id):
        """
        Get the principals that have been granted a role. Return the list of
        (principal id, setting) who have been assigned or removed from a role.
        If no principals have been assigned this role, then the empty list is
        returned.
        """
        return self._accumulate('getPrincipalsForRole', role_id)

    def getRolesForPrincipal(self, principal_id):
        """
        Get the roles granted to a principal. Return the list of
        (role id, setting) assigned or removed from this principal. If no roles
        have been assigned to this principal, then the empty list is returned.
        """
        return self._accumulate('getRolesForPrincipal', principal_id)

    def getPrincipalsAndRoles(self):
        """
        Get all settings. Return all the principal/role combinations along with
        the setting for each combination as a sequence of tuples with the role
        id, principal id, and setting, in that order.
        """
        return self._accumulate('getPrincipalsAndRoles')

    def _update_state(self, func_name, unused_check, *args):
        super_func = getattr(super(PersistentSiteRoleManager, self), func_name)
        result = super_func(*args)
        util = self._site_role_manager_utility
        if util is not None:
            util_func = getattr(util, func_name)
            # Since we do not have an auth utility that can validate principal
            # existence, we will force check to False.
            util_func(*args, check=False)
        return result

    def assignRoleToPrincipal(self, role_id, principal_id, check=False):
        self._update_state('assignRoleToPrincipal', check, role_id,
                           principal_id)

    def removeRoleFromPrincipal(self, role_id, principal_id, check=False):
        self._update_state('removeRoleFromPrincipal', check, role_id,
                           principal_id)

    def unsetRoleForPrincipal(self, role_id, principal_id, check=False):
        self._update_state('unsetRoleForPrincipal', check, role_id,
                           principal_id)


deferredimport.initialize()
deferredimport.deprecated(
    "Moved to nti.site",
    _TrivialSite="nti.site.transient:TrivialSite",
    get_site_for_site_names="nti.site.site:get_site_for_site_names",
    synchronize_host_policies="nti.site.hostpolicy:synchronize_host_policies",
    run_job_in_all_host_sites="nti.site.hostpolicy:run_job_in_all_host_sites")
