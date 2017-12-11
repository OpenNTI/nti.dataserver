#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import contains
from hamcrest import assert_that

from zope.securitypolicy.interfaces import Allow

from zope.securitypolicy.principalrole import principalRoleManager

from nti.testing import base


class TestZcml(base.ConfiguringTestBase):

    def test_directives(self):
        zcml = u"""
		<configure	xmlns="http://namespaces.zope.org/zope"
                    xmlns:zcml="http://namespaces.zope.org/zcml"
                    xmlns:sp="http://nextthought.com/ntp/securitypolicy"
                    i18n_domain="nti.actions.courseware_reports.view_reports">

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
