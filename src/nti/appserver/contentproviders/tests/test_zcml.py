#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

import nti.testing.base

from zope import component

from zope.component.hooks import site

from zope.contentprovider.interfaces import IContentProvider

from nti.appserver.policies.sites import BASECOPPA

from nti.site.transient import TrivialSite as _TrivialSite

ZCML_STRING = u"""
<configure xmlns="http://namespaces.zope.org/zope"
	xmlns:zcml="http://namespaces.zope.org/zcml"
	xmlns:cp="http://nextthought.com/ntp/contentproviders"
	i18n_domain='nti.dataserver'>

	<include package="zope.component" />
	<include package="zope.annotation" />
	<include package="z3c.baseregistry" file="meta.zcml" />
	<include package="." file="meta.zcml" />

	<utility
		component="nti.appserver.policies.sites.BASECOPPA"
		provides="zope.interface.interfaces.IComponents"
		name="mathcounts.nextthought.com" />

	<cp:pyramidTemplate
		name='foo.bar'
		for='* * *'
		template='nti.appserver:templates/failed_username_recovery_email.txt' />

	<registerIn registry="nti.appserver.policies.sites.BASECOPPA">
		<cp:pyramidTemplate
			name='foo.bar'
			for='* * *'
			template='nti.appserver:templates/failed_username_recovery_email.pt' />
	</registerIn>
</configure>
"""


class TestZcml(nti.testing.base.ConfiguringTestBase):

    def test_site_registrations(self):
        self.configure_string(ZCML_STRING)
        assert_that(BASECOPPA.__bases__,
                    is_((component.globalSiteManager,)))

        top = component.getMultiAdapter((None, None, None),
                                        IContentProvider,
                                        name='foo.bar')
        assert_that(top,
                    has_property('__name__', 'nti.appserver:templates/failed_username_recovery_email.txt'))

        with site(_TrivialSite(BASECOPPA)):
            sub = component.getMultiAdapter((None, None, None),
                                            IContentProvider,
                                            name='foo.bar')
            assert_that(sub,
                        has_property('__name__', 'nti.appserver:templates/failed_username_recovery_email.pt'))
