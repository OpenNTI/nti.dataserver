#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import contains_string

from nti.testing.base import ConfiguringTestBase

from xml.sax.saxutils import escape

from zope import component

from zope.interface.interfaces import IComponents

from zope.configuration.exceptions import ConfigurationError

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener

ZCML_REGISTRATION = """
<configure  xmlns="http://namespaces.zope.org/zope"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            xmlns:zcml="http://namespaces.zope.org/zcml"
            xmlns:appsite="http://nextthought.com/ntp/appsite"
            xmlns:sp="http://nextthought.com/ntp/sitepolicy">

    <include package="zope.component" file="meta.zcml" />
    <include package="zope.security" file="meta.zcml" />
    <include package="zope.component" />
    <include package="nti.app.site" file="meta.zcml" />
    <include package="nti.appserver.policies" file="meta.zcml" />

    <!-- We can reference a global object as our base -->
    <appsite:createBaseComponents bases="nti.appserver.policies.sites.BASEADULT"
                                  name="%s" />

    <appsite:registerInNamedComponents registry="%s">
        <sp:createSitePolicy %s />
    </appsite:registerInNamedComponents>

</configure>"""


def _make_xml_attrs(**kwargs):
    return ' '.join(['%s="%s"' % (name, value) for name, value in kwargs.items() if value is not None])


def _config_for_site_with_policy(sitename, brand, display, username, alias, realname):
    site_attrs = _make_xml_attrs(brand=brand,
                                 display_name=display,
                                 com_username=username,
                                 com_alias=alias,
                                 com_realname=realname)
    return ZCML_REGISTRATION % (sitename, sitename, site_attrs)


def _local_components(sitename):
    return component.getGlobalSiteManager().getUtility(IComponents, name=sitename)


def _policy_for_site(sitename):
    component = _local_components(sitename)

    return component.getUtility(ICommunitySitePolicyUserEventListener)


class TestLocalSitePolicyZCML(ConfiguringTestBase):

    def test_local_site_policy(self):
        config = _config_for_site_with_policy(u'childsite',
                                              u'Brand',
                                              u'Display',
                                              u'comm.nextthought.com',
                                              u'Comm',
                                              u'Site Comm')
        self.configure_string(config)

        policy = _policy_for_site('childsite')

        assert_that(policy.BRAND, is_('Brand'))
        assert_that(policy.DISPLAY_NAME, is_('Display'))
        assert_that(policy.COM_USERNAME, is_('comm.nextthought.com'))
        assert_that(policy.COM_ALIAS, is_('Comm'))
        assert_that(policy.COM_REALNAME, is_('Site Comm'))

    def test_comm_invariant(self):
        config = _config_for_site_with_policy('childsite',
                                              'Brand',
                                              'Display',
                                              None,
                                              'Comm',
                                              'Site Comm')

        with self.assertRaises(ConfigurationError) as e:
            self.configure_string(config)

        assert_that(str(e.exception),
                    contains_string('com_username must be provided if com_alias or com_realname is specified.'))

    def test_escaped_chars(self):
        """
        Test XML escaped characters, probably only applicable for user-input
        brand name.
        """
        brand_name = escape(u'wow&<.,;>')
        config = _config_for_site_with_policy(u'childsite3',
                                              brand_name,
                                              u'Display',
                                              u'comm.nextthought.com',
                                              u'Comm',
                                              u'Site Comm')

        self.configure_string(config)

        policy = _policy_for_site('childsite3')

        assert_that(policy.BRAND, is_(u'wow&<.,;>'))
        assert_that(policy.DISPLAY_NAME, is_('Display'))
        assert_that(policy.COM_USERNAME, is_('comm.nextthought.com'))
        assert_that(policy.COM_ALIAS, is_('Comm'))
        assert_that(policy.COM_REALNAME, is_('Site Comm'))

