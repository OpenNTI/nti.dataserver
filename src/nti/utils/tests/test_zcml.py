#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property

from zope import component

from nti.utils.interfaces import ILDAP
from nti.utils.interfaces import IOAuthKeys

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

"""

LDAP_ZCML_STRING = HEAD_ZCML_STRING + """
	<ldap:registerLDAP
		id="nti-ldap"
		url="ldaps://ldaps.nextthought.com:636"
		username="jason.madden@nextthougt.com"
		password="NTI%26123"
		encoding="urlquote"
		baseDN="OU=Accounts" />
</configure>
"""

OAUTHKEYS_ZCML_STRING = HEAD_ZCML_STRING + """
	<oauth:registerOAuthKeys
		apiKey="abcd1234"
		secretKey="efgh5678" />
</configure>
"""

class TestZcml(nti.testing.base.ConfiguringTestBase):

	def test_ldap_registration(self):
		self.configure_string(LDAP_ZCML_STRING)
		ldap = component.queryUtility(ILDAP, name="nti-ldap")
		assert_that(ldap, is_not(none()))
		assert_that(ldap, verifiably_provides(ILDAP))
		assert_that(ldap, has_property('URL', "ldaps://ldaps.nextthought.com:636"))
		assert_that(ldap, has_property('Username', "jason.madden@nextthougt.com"))
		assert_that(ldap, has_property('Password', "NTI&123"))
		assert_that(ldap, has_property('BaseDN', "OU=Accounts"))

	def test_oauth_registration(self):
		self.configure_string(OAUTHKEYS_ZCML_STRING)
		keys = component.queryUtility(IOAuthKeys, name="abcd1234")
		assert_that(keys, is_(none()))
		keys = component.getUtility(IOAuthKeys)
		assert_that(keys, verifiably_provides(IOAuthKeys))
		assert_that(keys, has_property('APIKey', "abcd1234"))
		assert_that(keys, has_property('SecretKey', "efgh5678"))
