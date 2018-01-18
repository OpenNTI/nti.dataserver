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

from zope import component

from zope.component.hooks import site
from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.settings import Deny
from zope.securitypolicy.settings import Allow

from z3c.baseregistry.baseregistry import BaseComponents

from nti.appserver.policies.sites import BASECOPPA as MATHCOUNTS

from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.authorization import is_site_admin

from nti.dataserver.interfaces import ISiteRoleManager

from nti.dataserver.users.users import User

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
            name="mytest.nextthought.com" />

        <utility
            component="nti.appserver.policies.sites.BASECOPPA"
            provides="zope.component.interfaces.IComponents"
            name="mathcounts.nextthought.com" />

        <registerIn registry="nti.dataserver.tests.test_site._MYSITE">
            <!-- Setup some site level admins -->
            <utility factory="nti.dataserver.site.SiteRoleManager"
                     provides="nti.dataserver.interfaces.ISiteRoleManager" />

            <sp:grantSite role="role:nti.dataserver.site-admin" principal="chris"/>
        </registerIn>
    </configure>
"""

_MYSITE = BaseComponents(MATHCOUNTS, name='test.components',
                         bases=(MATHCOUNTS,))

_MYSITE2 = BaseComponents(MATHCOUNTS, name='test.components2',
                          bases=(MATHCOUNTS,))


from nti.testing.base import ConfiguringTestBase


class TestSiteRoleManager(ConfiguringTestBase):

    def test_site_role_manager(self):

        self.configure_string(ZCML_STRING)
        user = User(u'chris')

        with site(_TrivialSite(_MYSITE)):
            # we have ISiteRoleManager
            srm = component.queryUtility(ISiteRoleManager)
            assert_that(srm, is_not(None))

            # which is not what we get when we adapt our site to
            # an IPrincipalRoleManager
            site_prm = IPrincipalRoleManager(getSite())
            assert_that(site_prm, is_not(srm))

            principals = site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN_NAME)
            assert_that(principals, contains(('chris', Allow,)))

            assert_that(is_site_admin(user), is_(True))

            # Can override configured allows
            site_prm.removeRoleFromPrincipal(ROLE_SITE_ADMIN_NAME, 'chris')
            principals = site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN_NAME)
            assert_that(principals, has_item(('chris', Deny,)))

            # Persistent registrations can be removed
            site_prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, 'mortimer')
            principals = site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN_NAME)
            assert_that(principals, has_items(('chris', Deny,),
                                              ('mortimer', Allow,)))

            site_prm.removeRoleFromPrincipal(ROLE_SITE_ADMIN_NAME)
            principals = site_prm.getPrincipalsForRole(ROLE_SITE_ADMIN_NAME)
            assert_that(principals, has_items(('chris', Deny,),
                                              ('mortimer', Deny,)))

        # Parent site not a site admin
        with site(_TrivialSite(MATHCOUNTS)):
            assert_that(is_site_admin(user), is_(False))

        # Not an admin to sibling site either
        with site(_TrivialSite(_MYSITE2)):
            assert_that(is_site_admin(user), is_(False))
