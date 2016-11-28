#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import empty
from hamcrest import is_
from hamcrest import is_not

from zope import component
from zope import interface

from zope.component.hooks import site
from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.settings import Allow

from nti.appserver.policies.sites import BASECOPPA as MATHCOUNTS

from nti.dataserver.interfaces import ISiteRoleManager

from nti.site.transient import TrivialSite as _TrivialSite

from nti.testing.base import ConfiguringTestBase

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

from z3c.baseregistry.baseregistry import BaseComponents
_MYSITE = BaseComponents(MATHCOUNTS, name='test.components', bases=(MATHCOUNTS,))

class TestSiteRoleManager(ConfiguringTestBase):

	def test_site_role_manager(self):

		self.configure_string(ZCML_STRING)

		with site(_TrivialSite(_MYSITE)):
			# we have ISiteRoleManager
			srm = component.queryUtility(ISiteRoleManager)
			assert_that(srm, is_not(None))

			# which is what we get when we adapt our site to
			# an IPrincipalRoleManager
			site_prm = IPrincipalRoleManager(getSite())
			assert_that(site_prm, is_(srm))

			principals = site_prm.getPrincipalsForRole('role:nti.dataserver.site-admin')
			assert_that(principals, contains(('chris', Allow, )))

