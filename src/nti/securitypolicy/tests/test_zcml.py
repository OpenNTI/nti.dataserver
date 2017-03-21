#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import contains
from hamcrest import assert_that

from zope.securitypolicy.interfaces import Allow

from zope.securitypolicy.principalrole import principalRoleManager

from nti.testing import base


class TestZcml(base.ConfiguringTestBase):

    def test_directives(self):
        zcml = """
		<configure	xmlns="http://namespaces.zope.org/zope"
			xmlns:sp="http://nextthought.com/ntp/securitypolicy"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:z3c="http://namespaces.zope.org/z3c"
			i18n_domain="nti.app.products.courseware_reports">

		<include file="meta.zcml" package="zope.component" />
		<include file="meta.zcml" package="zope.security" />
		<include file="meta.zcml" package="nti.securitypolicy" />

		<include package="zope.principalregistry" />

		<permission
			id="nti.actions.courseware_reports.view_reports"
			title="View reports" />

		<sp:role
			id="nti.roles.courseware.report_viewer"
			title="Globally accessible report viewing"
			description="Other people perhaps not associated with the course at
				all might also be able to view reports." />

		<sp:grant
			permission="nti.actions.courseware_reports.view_reports"
			role="nti.roles.courseware.report_viewer" />

		<sp:principal
			id="grey.allman@nextthought.com"
			login="grey.allman@nextthought.com"
			title="Grey Allman" />

		<sp:grant principal="grey.allman@nextthought.com"
			   role="nti.roles.courseware.report_viewer" />

		</configure>
		"""

        self.configure_string(zcml)

        assert_that(principalRoleManager.getRolesForPrincipal('grey.allman@nextthought.com'),
                    contains(('nti.roles.courseware.report_viewer', Allow)))
