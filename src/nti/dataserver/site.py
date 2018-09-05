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

from zope.component.hooks import getSite

from zope.interface import ro

from zope.interface.interfaces import IComponents

from zope.securitypolicy.interfaces import Unset
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.principalrole import PrincipalRoleManager
from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from zope.traversing.interfaces import IEtcNamespace

from nti.common.datastructures import ObjectHierarchyTree

from nti.dataserver.interfaces import ISiteHierarchy
from nti.dataserver.interfaces import ISiteRoleManager

from nti.externalization.persistence import NoPickle

from nti.site.interfaces import IMainApplicationFolder

from nti.site.site import get_component_hierarchy_names

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

    We never want to update the in-memory site utility.

    By returning these items in order (ourselves, utility, parent(s)), we
    are relying on zope security accepting the first applicable setting.
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

    def _get_parent_site(self, current_site, parent_site_name):
        # Since we already within a site, we need to go up into the sites folder
        # to fetch our parent site
        sites_folder = current_site.__parent__
        return sites_folder[parent_site_name]

    def _get_parent_site_role_manager(self, current_site):
        """
        Return the :class:`ISiteRoleManager` for our parent site.

        Note we do not recursively iterate through the parents.

        XXX: Since we do not run this in the parent site, we would not get any
        registered/configured users from a utility registered in the parent site.
        """
        current_site_name = current_site.__name__
        site_names = get_component_hierarchy_names()
        for site_name in site_names or ():
            if site_name != current_site_name:
                parent_site = self._get_parent_site(current_site, site_name)
                if parent_site is not current_site:
                    parent_role_manager = IPrincipalRoleManager(parent_site, None)
                    return parent_role_manager
                return None

    def _accumulate(self, func_name, *args):
        """
        Call the given `func_name` on ourselves, adding to the result found in
        the utility.
        """
        super_func = getattr(super(PersistentSiteRoleManager, self), func_name)
        result = super_func(*args)
        result = result or []
        current_site = getSite()
        if      self.__parent__ != getSite() \
            and self.__parent__.__name__ != 'dataserver2':
            # We are a parent IPrincipalRoleManager fetched in another site.
            # Must eject here to avoid recursion issues (and duplicate work).
            return result

        util = self._site_role_manager_utility
        if self.__parent__.__name__ == 'dataserver2':
            # This may not be entirely correct. We're getting configured
            # principals/roles registered in the current site while in the
            # IPrincipalRoleManager of the dataserver2 folder. If these
            # configured principals are moved to the persistent site role
            # manager, those users would lose whatever access they have from
            # this block.
            role_managers = (util,)
        else:
            parent_role_manager = self._get_parent_site_role_manager(current_site)
            role_managers = (util, parent_role_manager)
        for other_role_manager in role_managers:
            if other_role_manager is None:
                continue
            util_func = getattr(other_role_manager, func_name)
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


@interface.implementer(ISiteHierarchy)
class _SiteHierarchyTree(object):

    def get_tree(self):
        tree = ObjectHierarchyTree()

        # Exerpted from nti.site.hostpolicy
        sites = component.getUtility(IEtcNamespace, name='hostsites')
        ds_folder = sites.__parent__
        tree.set_root(ds_folder)
        assert IMainApplicationFolder.providedBy(ds_folder)

        # Ok, find everything that is globally registered
        global_sm = component.getGlobalSiteManager()
        all_global_named_utilities = list(global_sm.getUtilitiesFor(IComponents))
        for name, comp in all_global_named_utilities:
            # The sites must be registered the same as their internal name
            assert name == comp.__name__
        all_global_utilities = [x[1] for x in all_global_named_utilities]
        site_ro = [ro.ro(x) for x in all_global_utilities]
        # Work up the inheritance chain for each component and add it to the tree
        for comps in site_ro:
            comps = reversed(comps)
            for comp in comps:
                name = comp.__name__
                if name.endswith('base') or name.startswith('base'):
                    continue
                parent_name = comp.__bases__[0].__name__
                if parent_name.endswith('base') or parent_name.startswith('base'):
                    parent = ds_folder
                else:
                    parent = sites[parent_name]
                tree.add(sites[name], parent=parent)
        return tree

deferredimport.initialize()
deferredimport.deprecated(
    "Moved to nti.site",
    _TrivialSite="nti.site.transient:TrivialSite",
    get_site_for_site_names="nti.site.site:get_site_for_site_names",
    synchronize_host_policies="nti.site.hostpolicy:synchronize_host_policies",
    run_job_in_all_host_sites="nti.site.hostpolicy:run_job_in_all_host_sites")
