#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

from nose.tools import assert_raises

from nti.testing.matchers import is_empty

from zope import component
from zope import interface

from zope.component.hooks import site

from zope.configuration.exceptions import ConfigurationError

from pyramid.request import Request

from nti.appserver.policies.sites import BASECOPPA as MATHCOUNTS

from nti.appserver.interfaces import IAuthenticatedUserLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICoppaUser

from nti.dataserver.users.users import User

from nti.site.transient import TrivialSite as _TrivialSite

import nti.testing.base

ZCML_STRING = u"""
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:zcml="http://namespaces.zope.org/zcml"
           xmlns:link="http://nextthought.com/ntp/link_providers"
           i18n_domain='nti.dataserver'>

    <include package="zope.component" />
    <include package="zope.annotation" />
    <include package="z3c.baseregistry" file="meta.zcml" />
    <include package="." file="meta.zcml" />

    <utility
        component="nti.appserver.policies.sites.BASECOPPA"
        provides="zope.interface.interfaces.IComponents"
        name="mathcounts.nextthought.com" />

    <registerIn registry="nti.appserver.policies.sites.BASECOPPA">
        <link:userLink
            name='foo.bar'
            minGeneration='1234'
            url='/relative/path'
            for='nti.dataserver.interfaces.ICoppaUser' />
        <link:userLink
            named='nti.appserver.logon.REL_PERMANENT_TOS_PAGE'
            url='https://docs.google.com/document/pub?id=1rM40we-bbPNvq8xivEKhkoLE7wmIETmO4kerCYmtISM&amp;embedded=true'
            mimeType='text/html'
            for='nti.appserver.link_providers.tests.test_zcml.IMarker' />
    </registerIn>

    <utility
        component="nti.appserver.link_providers.tests.test_zcml._MYSITE"
        provides="zope.interface.interfaces.IComponents"
        name="mytest.nextthought.com" />

    <registerIn registry="nti.appserver.link_providers.tests.test_zcml._MYSITE">
        <link:userLink
            named='nti.appserver.logon.REL_PERMANENT_TOS_PAGE'
            url='https://this/link/overrides/the/parent'
            mimeType='text/html'
            for='nti.appserver.link_providers.tests.test_zcml.IMarker' />

        <link:missingUserLink
            named='nti.appserver.logon.REL_PERMANENT_TOS_PAGE'
            url='https://this/link/overrides/the/parent-missinguser'
            mimeType='text/html' />
    </registerIn>

</configure>
"""

from z3c.baseregistry.baseregistry import BaseComponents
_MYSITE = BaseComponents(MATHCOUNTS,
                         name='test.components',
                         bases=(MATHCOUNTS,))


class IMarker(IUser):
    pass


from nti.appserver.link_providers import provide_links
from nti.appserver.link_providers import unique_link_providers


class TestZcml(nti.testing.base.ConfiguringTestBase):

    def test_site_registrations(self):
        self.configure_string(ZCML_STRING)
        assert_that(MATHCOUNTS.__bases__,
                    is_((component.globalSiteManager,)))

        with site(_TrivialSite(MATHCOUNTS)):
            user = User(u'foo@bar')
            request = Request.blank('/')
            # Nothing until we provide ICoppaUser
            assert_that(list(component.subscribers((user, request), IAuthenticatedUserLinkProvider)),
                        is_empty())

            interface.alsoProvides(user, ICoppaUser)

            providers = list(component.subscribers((user, request),
                                                   IAuthenticatedUserLinkProvider))
            assert_that(providers, has_length(1))

            # Make sure all our properties got where we wanted them
            provider = providers[0]
            assert_that(provider.url, is_('/relative/path'))
            assert_that(provider.minGeneration, is_('1234'))

            assert_that(provider.get_links(), has_length(1))
            assert_that(provider.get_links()[0].elements[-1], is_('foo.bar'))

            provider.delete_link(provider.__name__)

            assert_that(provider.get_links(), is_empty())

    def test_raises(self):
        from nti.appserver.link_providers.zcml import registerUserLink

        context = object()
        with assert_raises(ConfigurationError):
            registerUserLink(context, name="name", named="named")
        with assert_raises(ConfigurationError):
            registerUserLink(context, name='')

        with assert_raises(ConfigurationError):
            registerUserLink(context, name='link', for_=None)

        with assert_raises(ConfigurationError):
            registerUserLink(context, name='link', field='abc', url='def')
        with assert_raises(ConfigurationError):
            registerUserLink(context, name='link',
                             field='abc', minGeneration='def')
        with assert_raises(ConfigurationError):
            registerUserLink(context, name='link',
                             field='abc', view_named='def')

    def test_site_registrations_do_not_accumulate(self):
        self.configure_string(ZCML_STRING)
        with site(_TrivialSite(_MYSITE)):
            user = User(u'foo@bar')
            request = Request.blank('/')
            # Nothing until we provide IMarker
            assert_that(list(component.subscribers((user, request), IAuthenticatedUserLinkProvider)),
                        is_empty())

            interface.alsoProvides(user, IMarker)

            links = list(provide_links(user, request))
            assert_that(links, has_length(1))

            # Make sure all our properties got where we wanted them
            link = links[0]
            __traceback_info__ = link.__dict__
            assert_that(link,
                        has_property('_v_provided_by',
                                     has_property('url', 'https://this/link/overrides/the/parent')))

            providers = list(unique_link_providers(user, request))
            assert_that(providers, has_length(1))
            assert_that(providers[0],
                        has_property('url', 'https://this/link/overrides/the/parent'))

    def test_missing_user_registrations(self):
        self.configure_string(ZCML_STRING)
        with site(_TrivialSite(_MYSITE)):
            user = User(u'foo@bar')
            request = Request.blank('/')
            
            assert_that(list(component.subscribers((request,), IUnauthenticatedUserLinkProvider)),
                        has_length(1))
            
            links = list(provide_links(None, request))
            assert_that(links, has_length(1))
            # Make sure all our properties got where we wanted them
            link = links[0]
            __traceback_info__ = link.__dict__
            assert_that(link,
                        has_property('_v_provided_by',
                                     has_property('url', 'https://this/link/overrides/the/parent-missinguser')))

            providers = list(unique_link_providers(None, request))
            assert_that(providers, has_length(1))
            assert_that(providers[0],
                        has_property('url', 'https://this/link/overrides/the/parent-missinguser'))
