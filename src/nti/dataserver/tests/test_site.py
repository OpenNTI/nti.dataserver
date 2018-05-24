#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import contains
from hamcrest import has_item
from hamcrest import has_items
from hamcrest import assert_that
from hamcrest import contains_inanyorder

import fudge

from zope import component

from zope.component.hooks import site
from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.settings import Deny
from zope.securitypolicy.settings import Allow

from z3c.baseregistry.baseregistry import BaseComponents

from nti.appserver.policies.sites import BASECOPPA

from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.authorization import is_site_admin

from nti.dataserver.interfaces import ISiteRoleManager

from nti.dataserver.users.users import User

from nti.testing.base import ConfiguringTestBase

from nti.site.transient import TrivialSite as _TrivialSite


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

        <registerIn registry="nti.dataserver.tests.test_site._MYSITE">
            <!-- Setup some site level admins -->
            <utility factory="nti.dataserver.site.SiteRoleManager"
                     provides="nti.dataserver.interfaces.ISiteRoleManager" />

            <sp:grantSite role="role:nti.dataserver.site-admin" principal="chris"/>
        </registerIn>
    </configure>
"""

_MYSITE = BaseComponents(BASECOPPA, name='test.components',
                         bases=(BASECOPPA,))

_MYSITE2 = BaseComponents(BASECOPPA, name='test.components2',
                          bases=(BASECOPPA,))


class TestSiteRoleManager(ConfiguringTestBase):

    @fudge.patch('nti.dataserver.site.PersistentSiteRoleManager._get_parent_site_role_manager')
    def test_site_role_manager(self, mock_get_parent_rm):
        fake_get_parent_sm =  mock_get_parent_rm.is_callable()
        fake_get_parent_sm.returns(None)

        self.configure_string(ZCML_STRING)
        user = User(u'chris')
        parent_site_admin_name = 'parent_site_admin'
        parent_user = User(parent_site_admin_name)

        with site(_TrivialSite(BASECOPPA)):
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
            fake_get_parent_sm.returns(parent_site_prm)
            fake_get_parent_sm.next_call().returns(None)

        with site(_TrivialSite(_MYSITE)):
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
        with site(_TrivialSite(_MYSITE2)):
            set_fake_parent_sm()
            assert_that(is_site_admin(user), is_(False))
            set_fake_parent_sm()
            assert_that(is_site_admin(parent_user), is_(True))
