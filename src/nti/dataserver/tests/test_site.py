#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ,too-many-function-args

from hamcrest import is_
from hamcrest import is_not
from hamcrest import contains
from hamcrest import has_item
from hamcrest import has_items
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder
does_not = is_not

import fudge

import unittest

from z3c.baseregistry.baseregistry import BaseComponents

from zope import component

from zope.component import globalSiteManager as BASE

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from zope.component.interfaces import ISite
from zope.component.interfaces import IComponents

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.settings import Deny
from zope.securitypolicy.settings import Allow

from zope.site.interfaces import INewLocalSite

from zope.traversing.interfaces import IEtcNamespace

from nti.appserver.policies.sites import BASEADULT
from nti.appserver.policies.sites import BASECOPPA

from nti.dataserver.authorization import ROLE_SITE_ADMIN
from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.authorization import is_site_admin

from nti.dataserver.interfaces import ISiteAdminManagerUtility
from nti.dataserver.interfaces import ISiteHierarchy
from nti.dataserver.interfaces import ISiteRoleManager

from nti.dataserver.site import _SiteHierarchyTree
from nti.dataserver.site import DefaultSiteAdminManagerUtility
from nti.dataserver.site import ImmediateParentSiteAdminManagerUtility
from nti.dataserver.site import PersistentSiteRoleManager

from nti.dataserver.users.users import User

from nti.dataserver.tests import SharedConfiguringTestLayer

from nti.testing.base import ConfiguringTestBase

from nti.site.hostpolicy import synchronize_host_policies

from nti.site.interfaces import IHostPolicySiteManager

from nti.site.transient import TrivialSite as _TrivialSite

from nti.site.site import get_site_for_site_names

from nti.site.tests import WithMockDS
from nti.site.tests import mock_db_trans


ZCML_STRING = """
    <configure xmlns="http://namespaces.zope.org/zope"
        xmlns:zcml="http://namespaces.zope.org/zcml"
        xmlns:link="http://nextthought.com/ntp/link_providers"
        xmlns:sp="http://nextthought.com/ntp/securitypolicy"
        i18n_domain='nti.dataserver'>

        <include package="zope.component" />
        <include package="zope.annotation" />

        <include package="z3c.baseregistry" file="meta.zcml" />

        <include package="nti.securitypolicy" file="meta.zcml" />
        <include package="nti.dataserver"/>

        <utility
            component="nti.dataserver.tests.test_site._MYSITE"
            provides="zope.component.interfaces.IComponents"
            name="test.components" />

        <utility
            component="nti.dataserver.tests.test_site._MYSITE2"
            provides="zope.component.interfaces.IComponents"
            name="test.components2" />

        <utility
            component="nti.appserver.policies.sites.BASECOPPA"
            provides="zope.component.interfaces.IComponents"
            name="genericcoppabase" />

        <utility
            component="nti.appserver.policies.sites.BASEADULT"
            provides="zope.component.interfaces.IComponents"
            name="genericadultbase" />

        <utility
            component="nti.dataserver.tests.test_site.EVAL"
            provides="zope.component.interfaces.IComponents"
            name="eval.nextthoughttest.com" />

        <utility
            component="nti.dataserver.tests.test_site.EVALALPHA"
            provides="zope.component.interfaces.IComponents"
            name="eval-alpha.nextthoughttest.com" />

        <utility
            component="nti.dataserver.tests.test_site.DEMO"
            provides="zope.component.interfaces.IComponents"
            name="demo.nextthoughttest.com" />

        <utility
            component="nti.dataserver.tests.test_site.DEMOALPHA"
            provides="zope.component.interfaces.IComponents"
            name="demo-alpha.nextthoughttest.com" />

        <registerIn registry="nti.appserver.policies.sites.BASECOPPA">
            <utility factory="nti.dataserver.site.DefaultSiteAdminManagerUtility"
                     provides="nti.dataserver.interfaces.ISiteAdminManagerUtility" />
         </registerIn>

        <registerIn registry="nti.dataserver.tests.test_site._MYSITE">
            <!-- Setup some site level admins -->
            <utility factory="nti.dataserver.site.SiteRoleManager"
                     provides="nti.dataserver.interfaces.ISiteRoleManager" />

            <sp:grantSite role="role:nti.dataserver.site-admin" principal="chris"/>
        </registerIn>

        <registerIn registry="nti.dataserver.tests.test_site.EVAL">
            <!-- Setup some site level admins -->
            <utility factory="nti.dataserver.site.SiteRoleManager"
                     provides="nti.dataserver.interfaces.ISiteRoleManager" />

            <utility factory="nti.dataserver.site.ImmediateParentSiteAdminManagerUtility"
                     provides="nti.dataserver.interfaces.ISiteAdminManagerUtility" />

            <utility factory="nti.dataserver.site._SiteHierarchyTree"
                     provides="nti.dataserver.interfaces.ISiteHierarchy" />
        </registerIn>
    </configure>
"""

_MYSITE = BaseComponents(BASECOPPA, name='test.components',
                         bases=(BASECOPPA,))

_MYSITE2 = BaseComponents(BASECOPPA, name='test.components2',
                          bases=(BASECOPPA,))

# Match a hierarchy we have in nti.app.sites.demo:
# global
#  \
#   eval
#   |\
#   | eval-alpha
#   \
#   demo
#    \
#     demo-alpha


EVAL = BaseComponents(BASEADULT,
                      name='eval.nextthoughttest.com',
                      bases=(BASEADULT,))

EVALALPHA = BaseComponents(EVAL,
                           name='eval-alpha.nextthoughttest.com',
                           bases=(EVAL,))

DEMO = BaseComponents(EVAL,
                      name='demo.nextthoughttest.com',
                      bases=(EVAL,))

DEMOALPHA = BaseComponents(DEMO,
                           name='demo-alpha.nextthoughttest.com',
                           bases=(DEMO,))

_SITES = (EVAL, EVALALPHA, DEMO, DEMOALPHA)


class TestSiteRoleManager(ConfiguringTestBase):

    @fudge.patch('nti.dataserver.site.PersistentSiteRoleManager._get_parent_site_role_managers')
    def test_site_role_manager(self, mock_get_parent_rm):
        fake_get_parent_sm =  mock_get_parent_rm.is_callable()
        fake_get_parent_sm.returns([])

        self.configure_string(ZCML_STRING)
        user = User(u'chris')
        parent_site_admin_name = 'parent_site_admin'
        parent_user = User(parent_site_admin_name)

        with current_site(_TrivialSite(BASECOPPA)):
            # Parent site not a site admin
            assert_that(is_site_admin(user), is_(False))

            # Grant user admin access in parent site
            parent_site_prm = IPrincipalRoleManager(getSite())
            assert_that(parent_site_prm, is_not(None))
            parent_site_prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME,
                                                  parent_site_admin_name)
            principals = parent_site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN_NAME)
            assert_that(principals, contains((parent_site_admin_name, Allow,)))
            assert_that(is_site_admin(parent_user), is_(True))

        def set_fake_parent_sm():
            fake_get_parent_sm =  mock_get_parent_rm.is_callable()
            fake_get_parent_sm.returns((parent_site_prm,))
            fake_get_parent_sm.next_call().returns(None)

        with current_site(_TrivialSite(_MYSITE)):
            # we have ISiteRoleManager
            srm = component.queryUtility(ISiteRoleManager)
            assert_that(srm, is_not(None))

            # which is not what we get when we adapt our site to
            # an IPrincipalRoleManager
            site_prm = IPrincipalRoleManager(getSite())
            assert_that(site_prm, is_not(srm))

            set_fake_parent_sm()
            principals = site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN_NAME)
            assert_that(principals, contains_inanyorder(('chris', Allow,),
                                                        (parent_site_admin_name, Allow,)))

            set_fake_parent_sm()
            assert_that(is_site_admin(user), is_(True))
            set_fake_parent_sm()
            assert_that(is_site_admin(parent_user), is_(True))

            # Can override configured allows
            site_prm.removeRoleFromPrincipal(ROLE_SITE_ADMIN_NAME, 'chris')
            set_fake_parent_sm()
            principals = site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN_NAME)
            assert_that(principals, has_items(('chris', Deny,),
                                              (parent_site_admin_name, Allow,)))

            # Persistent registrations can be removed
            site_prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, 'mortimer')
            set_fake_parent_sm()
            principals = site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN_NAME)
            assert_that(principals, has_items(('chris', Deny,),
                                              ('mortimer', Allow,),
                                              (parent_site_admin_name, Allow,)))

            site_prm.removeRoleFromPrincipal(ROLE_SITE_ADMIN_NAME, 'mortimer')
            set_fake_parent_sm()
            principals = site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN_NAME)
            assert_that(principals, has_items(('chris', Deny,),
                                              ('mortimer', Deny,),
                                              (parent_site_admin_name, Allow,)))

            set_fake_parent_sm()
            roles = site_prm.getRolesForPrincipal(parent_site_admin_name)
            assert_that(roles, has_item((ROLE_SITE_ADMIN_NAME, Allow,)))

            set_fake_parent_sm()
            site_prm.getPrincipalsAndRoles()

        # Not an admin to sibling site either
        with current_site(_TrivialSite(_MYSITE2)):
            set_fake_parent_sm()
            assert_that(is_site_admin(user), is_(False))
            set_fake_parent_sm()
            assert_that(is_site_admin(parent_user), is_(True))


class TestSiteHierarchy(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    _events = ()

    def setUp(self):
        super(TestSiteHierarchy, self).setUp()
        for site in _SITES:  # pylint: disable=redefined-outer-name
            # See explanation in nti.appserver.policies.sites; in short,
            # the teardown process can disconnect the resolution order of
            # these objects, and since they don't descend from the bases declared
            # in that module, they fail to get reset.
            site.__init__(site.__parent__, name=site.__name__, bases=site.__bases__)
            BASE.registerUtility(site, name=site.__name__, provided=IComponents)
        self._events = []
        # NOTE: We can't use an instance method; under
        # zope.testrunner, by the time tearDown is called, it's not
        # equal to the value it has during setUp, so we can't
        # unregister it!
        self._event_handler = lambda *args: self._events.append(args)
        BASE.registerHandler(self._event_handler, required=(IHostPolicySiteManager, INewLocalSite))
        BASE.registerUtility(DefaultSiteAdminManagerUtility(), ISiteAdminManagerUtility)
        BASE.registerUtility(_SiteHierarchyTree(), ISiteHierarchy)
        BASE.registerAdapter(PersistentSiteRoleManager, (ISite,), IPrincipalRoleManager)

    def tearDown(self):
        for site in _SITES:  # pylint: disable=redefined-outer-name
            BASE.unregisterUtility(site, name=site.__name__, provided=IComponents)
        BASE.unregisterHandler(self._event_handler, required=(IHostPolicySiteManager, INewLocalSite))
        BASE.unregisterUtility(DefaultSiteAdminManagerUtility(), ISiteAdminManagerUtility)
        BASE.unregisterUtility(_SiteHierarchyTree(), ISiteHierarchy)
        BASE.unregisterAdapter(PersistentSiteRoleManager, (ISite,), IPrincipalRoleManager)
        super(TestSiteHierarchy, self).tearDown()

    @WithMockDS
    def test_site_hierarchy(self):
        with mock_db_trans():
            synchronize_host_policies()
            synchronize_host_policies()

            host_sites_folder = component.getUtility(IEtcNamespace, name='hostsites')
            ds_folder = host_sites_folder.__parent__
            eval_site = get_site_for_site_names((EVAL.__name__,))
            alpha_site = get_site_for_site_names((EVALALPHA.__name__,))
            demo_site = get_site_for_site_names((DEMO.__name__,))
            demo_alpha_site = get_site_for_site_names((DEMOALPHA.__name__,))

            # Test cached tree
            sht = _SiteHierarchyTree()
            tree = sht.tree
            cached_tree = sht.tree
            assert_that(cached_tree, is_(tree))
            host_sites_folder.lastSynchronized = 123
            cached_tree = sht.tree
            assert_that(cached_tree, is_not(tree))

            assert_that(tree.lookup_func, is_(sht._lookup_func))

            # pylint: disable=no-member
            assert_that(tree.children_objects, contains_inanyorder(eval_site))
            assert_that(tree.children_objects, has_length(1))

            eval_node = tree.get_node_from_object(eval_site)
            assert_that(eval_node.children_objects, contains_inanyorder(alpha_site, demo_site))
            assert_that(eval_node.descendant_objects, contains_inanyorder(alpha_site, demo_site, demo_alpha_site))
            assert_that(eval_node.children_objects, has_length(2))
            assert_that(eval_node.descendant_objects, has_length(3))

            alpha_node = tree.get_node_from_object(alpha_site)
            assert_that(alpha_node.parent_object, is_(eval_site))
            assert_that(alpha_node.ancestor_objects, contains_inanyorder(eval_site, ds_folder))
            assert_that(alpha_node.sibling_objects, contains_inanyorder(demo_site))
            assert_that(alpha_node.children_objects, has_length(0))
            assert_that(alpha_node.descendant_objects, has_length(0))
            assert_that(alpha_node.sibling_objects, has_length(1))

            demo_alpha_node = tree.get_node_from_object(demo_alpha_site)
            assert_that(demo_alpha_node.parent_object, is_(demo_site))
            assert_that(demo_alpha_node.ancestor_objects, contains_inanyorder(eval_site, demo_site, ds_folder))
            assert_that(demo_alpha_node.ancestor_objects, has_length(3))
            assert_that(demo_alpha_node.children_objects, has_length(0))
            assert_that(demo_alpha_node.descendant_objects, has_length(0))
            assert_that(demo_alpha_node.sibling_objects, has_length(0))

        # No new sites created
        assert_that(self._events, has_length(len(_SITES)))

    @WithMockDS
    def test_default_site_admin_manager(self):
        with mock_db_trans():
            synchronize_host_policies()
            demo_alpha_site = get_site_for_site_names((DEMOALPHA.__name__,))
            eval_site = get_site_for_site_names((EVAL.__name__,))

            with current_site(demo_alpha_site):
                user = User(u'SiteAdmin')
                demo_alpha_prm = IPrincipalRoleManager(getSite())
                demo_alpha_prm.assignRoleToPrincipal(ROLE_SITE_ADMIN.id, user)
                principals = demo_alpha_prm.getPrincipalsForRole(ROLE_SITE_ADMIN.id)
                assert_that(principals, contains_inanyorder((user, Allow,)))

                demo_alpha_prm.removeRoleFromPrincipal(ROLE_SITE_ADMIN.id, user)
                principals = demo_alpha_prm.getPrincipalsForRole(ROLE_SITE_ADMIN.id)
                assert_that(principals, contains_inanyorder((user, Deny,)))

                # While in child site, validate we can get parent site
                # children accurately.
                site_admin_utility = component.getUtility(ISiteAdminManagerUtility)
                child_sites = site_admin_utility.get_descendant_site_names(eval_site)
                assert_that(child_sites,
                            contains_inanyorder(u'demo.nextthoughttest.com',
                                                u'demo-alpha.nextthoughttest.com',
                                                u'eval-alpha.nextthoughttest.com'))

    @WithMockDS
    def test_immediate_site_admin_manager(self):
        with mock_db_trans():
            synchronize_host_policies()
            eval_site = get_site_for_site_names((EVAL.__name__,))
            demo_site = get_site_for_site_names((DEMO.__name__,))
            alpha_site = get_site_for_site_names((EVALALPHA.__name__,))
            demo_alpha_site = get_site_for_site_names((DEMOALPHA.__name__,))

            with current_site(demo_alpha_site):
                user = User(u'SiteAdmin')
                psm = getSite().getSiteManager()
                psm.unregisterUtility(DefaultSiteAdminManagerUtility(), ISiteAdminManagerUtility)
                psm.registerUtility(ImmediateParentSiteAdminManagerUtility(), ISiteAdminManagerUtility)
                demo_alpha_prm = IPrincipalRoleManager(getSite())
                demo_alpha_prm.assignRoleToPrincipal(ROLE_SITE_ADMIN.id, user)
                principals = demo_alpha_prm.getPrincipalsForRole(ROLE_SITE_ADMIN.id)
                # Permission in demo-alpha and the immediate parent (demo)
                assert_that(principals, contains_inanyorder((user, Allow,), (user, Allow,)))

                demo_alpha_prm.removeRoleFromPrincipal(ROLE_SITE_ADMIN.id, user)
                principals = demo_alpha_prm.getPrincipalsForRole(ROLE_SITE_ADMIN.id)
                assert_that(principals, contains_inanyorder((user, Deny,), (user, Deny,)))

            with current_site(eval_site):
                eval_site_prm = IPrincipalRoleManager(getSite())
                principals = eval_site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN.id)
                assert_that(principals, has_length(0))

            with current_site(demo_alpha_site):
                demo_alpha_prm.assignRoleToPrincipal(ROLE_SITE_ADMIN.id, user)

            with current_site(demo_site):
                demo_prm = IPrincipalRoleManager(getSite())
                principals = demo_prm.getPrincipalsForRole(ROLE_SITE_ADMIN.id)
                assert_that(principals, contains_inanyorder((user, Allow,)))

            with current_site(eval_site):
                eval_site_prm = IPrincipalRoleManager(getSite())
                principals = eval_site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN.id)
                assert_that(principals, has_length(0))

            with current_site(alpha_site):
                alpha_site_prm = IPrincipalRoleManager(getSite())
                principals = alpha_site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN.id)
                assert_that(principals, has_length(0))
