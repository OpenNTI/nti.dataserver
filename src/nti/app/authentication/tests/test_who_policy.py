#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_items
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import is_not as does_not
from hamcrest import contains_inanyorder

from nti.testing.time import time_monotonically_increases

import fudge
import unittest

from pyramid.interfaces import IRequest

from pyramid.request import Request

from pyramid.security import Everyone
from pyramid.security import Authenticated

from zope import component
from zope import interface

from zope.authentication.interfaces import IEveryoneGroup

from nti.app.authentication.who_apifactory import create_who_apifactory

from nti.app.authentication.who_policy import AuthenticationPolicy

from nti.dataserver.interfaces import INoUserEffectivePrincipalResolver


class FakeGroupsCallback(object):

    def __call__(self, unused_identity, unused_request):
        return (self.principal,)


class TestWhoPolicy(unittest.TestCase):

    def setUp(self):
        self.api_factory = create_who_apifactory()
        self.policy = AuthenticationPolicy(self.api_factory.default_identifier_name,
                                           api_factory=self.api_factory)

    @time_monotonically_increases
    def test_reissue(self,):
        mock_get = fudge.Fake()
        mock_get.is_callable().returns({'login_app_root': '/login'})
        with fudge.patched_context('zope.component', 'getUtility', mock_get):
            policy = self.policy
            request = Request.blank('/')
            headers = policy.remember(request, 'jason')

            request = Request.blank('/', {'HTTP_COOKIE': headers[0][1]})

            api = policy._getAPI(request)
            ident = api.name_registry[policy._identifier_id]
            ident.userid_checker = None
            assert_that(policy.unauthenticated_userid(request),
                        is_('jason'))

            assert_that(request, does_not(has_property('_authtkt_reissued')))

            ident.reissue_time = 1

            assert_that(policy.unauthenticated_userid(request),
                        is_('jason'))
            # Side-effect: need a reissue
            assert_that(request, has_property('_authtkt_reissued'))

    def test_anonymous_effective_principles(self):

        @component.adapter(IRequest)
        @interface.implementer(INoUserEffectivePrincipalResolver)
        class AnonEffPrincipalProvider(object):

            def __init__(self, request):
                pass

            def effective_principals(self, unused_request):
                return ('nti-test-anon-principal@nt.com', )

        everyone_group = 'test_everyone_group'

        mock_get = fudge.Fake()
        mock_get.is_callable()
        mock_get.next_call().with_args(IEveryoneGroup).returns(everyone_group)
        with fudge.patched_context('zope.component', 'getUtility', mock_get):

            sm = component.getGlobalSiteManager()
            sm.registerSubscriptionAdapter(AnonEffPrincipalProvider)
            try:
                policy = self.policy
                request = Request.blank('/')
                effective_principals = policy.effective_principals(request)
                assert_that(effective_principals, has_items(
                    Everyone, 'nti-test-anon-principal@nt.com'))
                assert_that(effective_principals, does_not(
                    has_items(Authenticated)))
            finally:
                sm.unregisterSubscriptionAdapter(AnonEffPrincipalProvider)

    def test_get_groups(self):
        callback = FakeGroupsCallback()
        callback.principal = 'fake-principal'

        policy = self.policy
        policy._callback = callback

        request = None
        identity = {}

        # A real identity gets the callback usernames, Everyone, and
        # Authenticated
        groups = policy._get_groups(identity, request)
        assert_that(groups, 
                    contains_inanyorder('fake-principal', Everyone, Authenticated))
