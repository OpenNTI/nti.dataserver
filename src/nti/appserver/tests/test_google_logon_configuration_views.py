#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import has_properties
from hamcrest import instance_of
from hamcrest import is_
from hamcrest import none
from hamcrest import same_instance

from pyramid.interfaces import IRequest

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.component.hooks import getSite

from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider
from nti.appserver.interfaces import IGoogleLogonLookupUtility
from nti.appserver.interfaces import IGoogleLogonSettings

from nti.appserver.logon import GoogleLogonSettings
from nti.appserver.logon import GoogleLogonLookupUtility
from nti.appserver.logon import SimpleUnauthenticatedUserGoogleLinkProvider
from nti.appserver.logon import SimpleMissingUserGoogleLinkProvider
from nti.appserver.logon import DefaultGoogleLogonLookupUtility

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.coremetadata.interfaces import IMissingUser

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users import User

from nti.dataserver.users.common import remove_user_creation_site
from nti.dataserver.users.common import set_user_creation_site
from nti.dataserver.users.common import user_creation_sitename

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class TestGoogleLogonConfigurationViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=(u'user001', u'admin001@nextthought.com'), testapp=True, default_authenticate=False)
    def test_enable_and_disable(self):
        extra_environ = self._make_extra_environ(username=u'admin001@nextthought.com')

        # enable
        enable_url = 'https://demo.nextthought.com/dataserver2/@@enable_google_logon'
        res = self.testapp.post_json(enable_url, status=200, extra_environ=extra_environ)
        assert_that(res.json_body, has_entries({'lookup_by_email': False,
                                                'restricted_domain': None}))

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.nextthought.com'):
            site_manager = getSite().getSiteManager()

            lookup = component.getUtility(IGoogleLogonLookupUtility)
            assert_that(lookup, instance_of(GoogleLogonLookupUtility))
            assert_that(lookup.__parent__, same_instance(site_manager))

            settings = component.getUtility(IGoogleLogonSettings)
            assert_that(settings, instance_of(GoogleLogonSettings))
            assert_that(settings.__parent__, same_instance(site_manager))

            subs = [x for x in site_manager.registeredSubscriptionAdapters()]
            assert_that(subs, has_length(2))

        # disable
        disable_url = 'https://demo.nextthought.com/dataserver2/@@disable_google_logon'
        res = self.testapp.post_json(disable_url, status=204, extra_environ=extra_environ)

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.nextthought.com'):
            # we have a global default one.
            lookup = component.getUtility(IGoogleLogonLookupUtility)
            assert_that(lookup, instance_of(DefaultGoogleLogonLookupUtility))

            settings = component.queryUtility(IGoogleLogonSettings)
            assert_that(settings, is_(None))

            subs = [x for x in site_manager.registeredSubscriptionAdapters()]
            assert_that(subs, has_length(0))
