#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that
from hamcrest import has_property

from zope import component
from zope.component.hooks import site

from nti.dataserver.site import _TrivialSite
from nti.appserver.policies.sites import BASECOPPA

from ..interfaces import ILDAP
from ..interfaces import IOAuthKeys

import nti.testing.base
from nti.testing.matchers import verifiably_provides

HEAD_ZCML_STRING = """
		<configure xmlns="http://namespaces.zope.org/zope"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:ldap="http://nextthought.com/ntp/ldap"
			xmlns:oauth="http://nextthought.com/ntp/oauth"
			i18n_domain='nti.dataserver'>

		<include package="zope.component" />
		<include package="zope.annotation" />
		<include package="z3c.baseregistry" file="meta.zcml" />

		<include package="." file="meta.zcml" />

		<utility
			component="nti.appserver.policies.sites.BASECOPPA"
			provides="zope.component.interfaces.IComponents"
			name="mathcounts.nextthought.com" />

		<registerIn registry="nti.appserver.policies.sites.BASECOPPA">
"""

LDAP_ZCML_STRING = HEAD_ZCML_STRING + """
	<ldap:registerLDAP
		id="nti-ldap"
		url="ldaps://ldaps.nextthought.com:636"
		username="jason.madden@nextthougt.com"
		password="NTI%26123"
		encoding="urlquote"
		baseDN="OU=Accounts" />
</registerIn>
</configure>
"""

OAUTHKEYS_ZCML_STRING = HEAD_ZCML_STRING + """
	<oauth:registerOAuthKeys
		apiKey="abcd1234"
		secretKey="efgh5678" />
</registerIn>
</configure>
"""

class TestZcml(nti.testing.base.ConfiguringTestBase):

	def test_site_ldap_registration(self):

		self.configure_string(LDAP_ZCML_STRING)
		assert_that(BASECOPPA.__bases__, is_((component.globalSiteManager,)))

		assert_that(component.queryUtility(ILDAP, name="nti-ldap"), is_(none()))

		with site(_TrivialSite(BASECOPPA)):
			ldap = component.getUtility(ILDAP, name="nti-ldap")
			assert_that(ldap, verifiably_provides(ILDAP))
			assert_that(ldap, has_property('URL', "ldaps://ldaps.nextthought.com:636"))
			assert_that(ldap, has_property('Username', "jason.madden@nextthougt.com"))
			assert_that(ldap, has_property('Password', "NTI&123"))
			assert_that(ldap, has_property('BaseDN', "OU=Accounts"))

	def test_site_oauth_registration(self):

		self.configure_string(OAUTHKEYS_ZCML_STRING)
		assert_that(BASECOPPA.__bases__, is_((component.globalSiteManager,)))

		assert_that(component.queryUtility(IOAuthKeys, name="abcd1234"), is_(none()))

		with site(_TrivialSite(BASECOPPA)):
			keys = component.getUtility(IOAuthKeys, name="abcd1234")
			assert_that(keys, verifiably_provides(IOAuthKeys))
			assert_that(keys, has_property('APIKey', "abcd1234"))
			assert_that(keys, has_property('SecretKey', "efgh5678"))

