#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import sys

from inspect import isclass

from ZODB.interfaces import IConnection

from persistent.persistence import Persistent

from zope import component
from zope import deferredimport
from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import CachedProperty
from zope.component import IFactory
from zope.component.factory import Factory

from zope.component.hooks import getSite

from zope.interface.interfaces import IComponents

from zope.securitypolicy.interfaces import Unset
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.principalrole import PrincipalRoleManager
from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from zope.site.interfaces import INewLocalSite

from zope.traversing.interfaces import IEtcNamespace

from nti.common.datastructures import ObjectHierarchyTree

from nti.dataserver.interfaces import ISiteHierarchy
from nti.dataserver.interfaces import ISiteConfigurable
from nti.dataserver.interfaces import ISiteConfigurableFactory
from nti.dataserver.interfaces import ISiteRequiredConfigurable
from nti.dataserver.interfaces import ISiteRoleManager
from nti.dataserver.interfaces import ISiteAdminManagerUtility

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.interfaces import IClassObjectFactory

from nti.externalization.persistence import NoPickle

from nti.site import get_all_host_sites

from nti.site.interfaces import IMainApplicationFolder

from nti.site.site import get_component_hierarchy_names

#: Common base for all COPPA sites components
BASECOPPA = u'genericcoppabase'

#: Common base for all the other non-COPPA site
BASEADULT = u"genericadultbase"

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
                # pylint: disable=no-member
                result = util.getSetting(role_id, principal_id,
                                         default=default)
        return result

    def _get_parent_site(self, current_site, parent_site_name):
        # Since we already within a site, we need to go up into the sites folder
        # to fetch our parent site
        sites_folder = current_site.__parent__
        return sites_folder[parent_site_name]

    def _get_parent_site_role_managers(self, current_site):
        """
        Return the :class:`ISiteRoleManager` for our parent site(s).

        Note we do not recursively iterate through the parents.

        XXX: Since we do not run this in the parent site, we would not get any
        registered/configured users from a utility registered in the parent site.
        """
        current_site_name = current_site.__name__
        site_names = get_component_hierarchy_names()
        result = []
        for site_name in site_names or ():
            if site_name != current_site_name:
                parent_site = self._get_parent_site(current_site, site_name)
                if parent_site is not current_site:
                    parent_role_manager = IPrincipalRoleManager(parent_site, None)
                    result.append(parent_role_manager)
        return result

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
            parent_role_managers = self._get_parent_site_role_managers(current_site)
            role_managers = [util]
            role_managers.extend(parent_role_managers)
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

    def _update_role(self, func_name, *args):
        super_func = getattr(super(PersistentSiteRoleManager, self), func_name)
        super_func(*args)
        site_admin_manager = component.getUtility(ISiteAdminManagerUtility)
        for site in site_admin_manager.get_sites_to_update():
            # If the site that you adapted to to get here is in this list,
            # the annotation will not work as expected
            principal_role_manager = IPrincipalRoleManager(site)
            super_func = getattr(super(PersistentSiteRoleManager, principal_role_manager),
                                 func_name)
            super_func(*args)

    def assignRoleToPrincipal(self, role_id, principal_id):
        self._update_role('assignRoleToPrincipal', role_id, principal_id)

    def removeRoleFromPrincipal(self, role_id, principal_id):
        self._update_role('removeRoleFromPrincipal', role_id, principal_id)


class DefaultSiteAdminManagerUtility(object):

    def get_sites_to_update(self):
        return []

    def _get_site(self, site, attr):
        site = site if site is not None else getSite()
        site_hierarchy_utility = component.getUtility(ISiteHierarchy)
        site_hierarchy = site_hierarchy_utility.tree
        site_node = site_hierarchy.get_node_from_object(site)
        # pylint: disable=unused-variable
        __traceback_info__ = u"Site: %s\nTree Root Descendants: %s\nSite Type: %s\n" \
                             u"Utility Lookup func result: %s\nTree lookup func result: %s", \
                             (site, site_hierarchy.root.descendant_objects, type(site),
                              site_hierarchy_utility._lookup_func(site), site_hierarchy.lookup_func(site))

        # If this node is None we want an error to be raised
        return getattr(site_node, attr)

    def get_parent_site(self, site=None):
        parent = self._get_site(site, 'parent_object')
        return parent

    def get_parent_name(self, site=None):
        return self.get_parent_site(site).__name__

    def get_ancestor_sites(self, site=None):
        ancestors = self._get_site(site, 'ancestor_objects')
        return ancestors

    def get_children_sites(self, site=None):
        ancestors = self._get_site(site, 'children_objects')
        return ancestors

    def get_children_site_names(self, site=None):
        return [s.__name__ for s in self.get_children_sites(site)]

    def get_ancestor_site_names(self, site=None):
        return [s.__name__ for s in self.get_ancestor_sites(site)]

    def get_descendant_sites(self, site=None):
        descendants = self._get_site(site, 'descendant_objects')
        return descendants

    def get_descendant_site_names(self, site=None):
        return [s.__name__ for s in self.get_descendant_sites(site)]

    def get_sibling_sites(self, site=None):
        siblings = self._get_site(site, 'sibling_objects')
        return siblings

    def get_sibling_site_names(self, site=None):
        return [s.__name__ for s in self.get_sibling_sites(site)]


class ImmediateParentSiteAdminManagerUtility(DefaultSiteAdminManagerUtility):

    def get_sites_to_update(self):
        sites = super(ImmediateParentSiteAdminManagerUtility, self).get_sites_to_update()
        current_site = getSite()
        site_hierarchy = component.getUtility(ISiteHierarchy)
        site_hierarchy = site_hierarchy.tree
        site_node = site_hierarchy.get_node_from_object(current_site)
        # pylint: disable=unused-variable
        __traceback_info__ = current_site
        sites.append(site_node.parent_object)
        try:  # Make sure we don't include dataserver2
            sites.remove(site_node.root.obj)
        except ValueError:
            pass
        return sites


@interface.implementer(ISiteHierarchy)
class _SiteHierarchyTree(object):

    @property
    def lastModified(self):
        sites = component.getUtility(IEtcNamespace, name='hostsites')
        return sites.lastSynchronized

    def _lookup_func(self, site):
        return site.__name__

    @CachedProperty('lastModified')
    def tree(self):
        tree = ObjectHierarchyTree('hostsites', None, lookup_func=self._lookup_func)
        sites = component.getUtility(IEtcNamespace, name='hostsites')
        ds_folder = sites.__parent__
        tree.set_root(ds_folder)
        assert IMainApplicationFolder.providedBy(ds_folder)

        # Work up the inheritance chain for each component and add it to the
        # tree
        for site in get_all_host_sites():
            site_component = component.getUtility(IComponents, name=site.__name__)
            # Ideally, we would use site_component.__parent__ here
            # but we have encountered some legacy code where the parent isn't in the site bases
            # Grabbing the bases[0] implies we are getting the first
            # fallback component registry
            parent_name = site_component.__bases__[0].__name__
            if parent_name.endswith('base') or parent_name.startswith('base'):
                parent = ds_folder
            else:
                parent = sites[parent_name]
            logger.debug(u'Adding site %s with parent %s', site, parent)
            tree.add(site, parent=parent)
        return tree


class UnsupportedSiteConfigurableType(Exception):
    pass


def persistent_utility_site_configurable_factory(configurable, site_manager):
    if not isclass(configurable):
        raise UnsupportedSiteConfigurableType(u'Persisting non-class type utilities is not supported.')
    # Order is important here. If we mark it before we register it, the registration won't be able to auto resolve
    # the interface it implements
    factory = configurable()
    ifaces = list(interface.implementedBy(configurable))
    if len(ifaces) != 1:
        raise UnsupportedSiteConfigurableType(u'Base class must implement exactly one interface.')
    iface = ifaces[0]
    connection = IConnection(site_manager)
    connection.add(factory)
    site_manager.registerUtility(factory, iface)
    interface.alsoProvides(factory, ISiteConfigurable)
    lifecycleevent.created(factory)
    return factory


def make_persistent(klass):
    # Check if we're already persistent
    if Persistent in klass.__bases__:
        return klass
    else:
        new_name = 'Persistent' + klass.__name__
        new_bases = (klass, PersistentCreatedModDateTrackingObject)
        # Add a metaclass to ensure persistent init is called
        class InitPersistence(type):
            def __call__(cls, *args, **kwargs):
                new_obj = type.__call__(cls, *args, **kwargs)
                super(Persistent, new_obj).__init__()
        # Create a new class with the added base
        new_klass = type(new_name, new_bases, dict(klass.__dict__))
        # Add our metaclass to make sure we initialize
        new_klass.__metaclass__ = InitPersistence
        # Now register this in the module so we can do pickling
        setattr(sys.modules[klass.__module__], new_name, new_klass)
        # Register a class factory for this so we can create it externally
        gsm = component.getGlobalSiteManager()
        gsm.registerAdapter(new_klass,
                            (object,),
                            IClassObjectFactory,
                            name=new_name)
        return new_klass


@interface.implementer(ISiteConfigurable)
class SiteConfigurable(object):

    configurable = None

    def __init__(self, description, action, persist=False, title=None, required=False):
        self.description = description
        self.action = action
        self.title = title
        self.persist = persist
        self.required = required

    def __call__(self, configurable):
        self.configurable = configurable
        title = configurable.__name__ if not self.title else self.title
        if self.persist:
            self.configurable = make_persistent(configurable)
        iface = ISiteConfigurable
        if self.required:
            iface = ISiteRequiredConfigurable
        factory = Factory(self._do_configuration,
                          title=title,
                          description=self.description,
                          interfaces=(iface,))
        gsm = component.getGlobalSiteManager()
        gsm.registerUtility(factory, IFactory, title)
        return configurable

    def _do_configuration(self, site_manager):
        factory = component.getMultiAdapter((self.configurable, site_manager),
                                            ISiteConfigurableFactory,
                                            self.action)
        return factory


@component.adapter(INewLocalSite)
def _on_site_created(site_manager):
    """
    Register all required site configurables
    """
    site_configurables = interface.getFactoriesFor(ISiteRequiredConfigurable)
    for configurable in site_configurables:
        configurable(site_manager)


deferredimport.initialize()
deferredimport.deprecated(
    "Moved to nti.site",
    _TrivialSite="nti.site.transient:TrivialSite",
    get_site_for_site_names="nti.site.site:get_site_for_site_names",
    synchronize_host_policies="nti.site.hostpolicy:synchronize_host_policies",
    run_job_in_all_host_sites="nti.site.hostpolicy:run_job_in_all_host_sites")
