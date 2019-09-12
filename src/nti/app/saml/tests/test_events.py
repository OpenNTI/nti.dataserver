#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import has_key
from hamcrest import equal_to
from hamcrest import assert_that
from hamcrest import has_entries

from nti.testing.matchers import validly_provides

import fudge

from saml2.saml import NAMEID_FORMAT_PERSISTENT

from zope import component
from zope import interface

from zope.component.hooks import site

from zope.event import notify

from pyramid.request import Request

from persistent.mapping import PersistentMapping

from nti.app.saml.events import SAMLUserCreatedEvent

from nti.app.saml.events import _user_created
from nti.app.saml.events import _user_removed

from nti.app.saml.interfaces import ISAMLNameId
from nti.app.saml.interfaces import ISAMLUserAssertionInfo
from nti.app.saml.interfaces import ISAMLAuthenticationResponse
from nti.app.saml.interfaces import ISAMLUserAuthenticatedEvent

from nti.dataserver.saml.interfaces import ISAMLProviderUserInfo
from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings

from nti.dataserver.users.users import User

from nti.schema.eqhash import EqHash

from nti.site.transient import TrivialSite

from nti.app.saml.tests.test_logon import IsolatedComponents

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


@interface.implementer(ISAMLUserAssertionInfo)
class TestSAMLUserAssertionInfo(object):

    def __init__(self, saml_response):
        for k, v in saml_response.items():
            setattr(self, k, v)


# ITestSAMLProviderUserInfo


@EqHash('provider_id')
@interface.implementer(ISAMLProviderUserInfo)
class TestSAMLProviderUserInfo(object):

    def __init__(self, user_assertion_info):
        self.email = user_assertion_info.email
        self.nameid = user_assertion_info.nameid
        self.lastname = user_assertion_info.lastname
        self.username = user_assertion_info.username
        self.firstname = user_assertion_info.firstname
        self.provider_id = user_assertion_info.provider_id


def assertion_info(provider_id, username, email, firstname, lastname):
    name_id = fudge.Fake('name_id').has_attr(nameid=u"testNameId",
                                             name_format=NAMEID_FORMAT_PERSISTENT,
                                             name_qualifier=provider_id,
                                             sp_name_qualifier=None)
    interface.alsoProvides(name_id, ISAMLNameId)
    return TestSAMLUserAssertionInfo({"provider_id": provider_id,
                                      "username": username,
                                      "nameid": name_id,
                                      "email": email,
                                      "firstname": firstname,
                                      "lastname": lastname,
                                      "realname": None})


class TestEvents(ApplicationLayerTest):

    @WithMockDSTrans
    def test_interfaces(self):
        ########
        # Setup
        user = User.create_user(username=u'testUser')
        request = Request.blank('/')

        #######
        # Test
        user_assertion_info = assertion_info(u"pid1",
                                             u"bradley@maycomb.com",
                                             u"bradley@maycomb.com",
                                             u"Boo",
                                             u"Radley")

        saml_response = fudge.Fake('saml_response')
        saml_response.has_property(ava=PersistentMapping)
        saml_response.provides('id').returns(u"fakesamlid")
        saml_response.provides('session_id').returns(u"fakesamlsessionid")
        saml_response.provides('session_info').returns({u"issuer": u"testIssuer"})
        interface.alsoProvides(saml_response, ISAMLAuthenticationResponse)

        user_created_event = SAMLUserCreatedEvent(u'harperProvider',
                                                  user,
                                                  user_assertion_info,
                                                  request,
                                                  saml_response)

        #######
        # Verify
        assert_that(user_created_event,
                    validly_provides(ISAMLUserAuthenticatedEvent))

    @WithMockDSTrans
    def test_user_creation_event(self):
        with site(TrivialSite(IsolatedComponents('nti.app.saml.tests',
                                                 bases=(component.getSiteManager(),)))):
            ########
            # Setup
            user = User.create_user(username=u'testUser')
            user_assertion_info = assertion_info(u"pid2",
                                                 u"mickey@mouse.com",
                                                 u"mickey@mouse.com",
                                                 u"Mickey",
                                                 u"Mouse")
            request = Request.blank('/')

            saml_response = fudge.Fake('saml_response')
            saml_response.provides('id').returns(u"fakesamlid")
            saml_response.provides('session_id').returns(u"fakesamlsessionid")
            saml_response.provides('session_info').returns( {u"issuer": u"testIssuer"})

            event = SAMLUserCreatedEvent(u'disneyProvider',
                                         user,
                                         user_assertion_info,
                                         request,
                                         saml_response)

            self.registerComponents()

            #######
            # Test
            #
            _user_created(event)

            #######
            # Verify

            expected_info = TestSAMLProviderUserInfo(user_assertion_info)
            actual_info = ISAMLIDPUserInfoBindings(user)['disneyProvider']
            assert_that(actual_info.__dict__,
                        has_entries(expected_info.__dict__))

    @WithMockDSTrans
    def test_existing_user_creation_event(self):

        with site(TrivialSite(IsolatedComponents('nti.app.saml.tests',
                                                 bases=(component.getSiteManager(),)))):
            ########
            # Setup
            user = User.create_user(username=u'testUser')
            user_assertion_info = assertion_info(u"pid2",
                                                 u"mickey@mouse.com",
                                                 u"mickey@mouse.com",
                                                 u"Mickey",
                                                 u"Mouse")

            saml_response = fudge.Fake('saml_response')
            saml_response.provides('id').returns(u"fakesamlid")
            saml_response.provides('session_id').returns(u"fakesamlsessionid")
            saml_response.provides('session_info').returns({u"issuer": u"testIssuer"})

            request = Request.blank('/')
            event = SAMLUserCreatedEvent('disneyProvider',
                                         user,
                                         user_assertion_info,
                                         request,
                                         saml_response)

            self.registerComponents()

            # Provide existing annotation for user object
            idp_user2_info = TestSAMLProviderUserInfo(
                assertion_info(u"sid3",
                               u"minnie@mouse.com",
                               u"minnie@mouse.com",
                               u"Minnie",
                               u"Mouse"))
            ISAMLIDPUserInfoBindings(user)['disneyProvider'] = idp_user2_info

            #######
            # Test

            # Ensure we get appropriate info (i.e. not idp_user_info2)
            _user_created(event)

            #######
            # Verify

            expected_info = TestSAMLProviderUserInfo(user_assertion_info)
            actual_info = ISAMLIDPUserInfoBindings(user)['disneyProvider']
            assert_that(actual_info, equal_to(expected_info))

            # clear
            _user_removed(user, None)

    @WithMockDSTrans
    def test_failure_to_adapt(self):
        ########
        # Setup
        user = User.create_user(username=u'testUser')
        user_assertion_info = assertion_info(u"pid2",
                                             u"mickey@mouse.com",
                                             u"mickey@mouse.com",
                                             u"Mickey",
                                             u"Mouse")
        request = Request.blank('/')
        event = component.getMultiAdapter(
            ('disneyProvider', user, user_assertion_info, request),
            ISAMLUserAuthenticatedEvent
        )

        #######
        # Test
        _user_created(event)

        #######
        # Verify
        assert_that(ISAMLIDPUserInfoBindings(user),
                    is_not(has_key('disneyProvider')))

    @WithMockDSTrans
    def test_handler_registration(self):

        with site(TrivialSite(IsolatedComponents('nti.app.saml.tests',
                                                 bases=(component.getSiteManager(),)))):
            ########
            # Setup
            user = User.create_user(username=u'testUser')
            user_assertion_info = assertion_info(u"pid2",
                                                 u"mickey@mouse.com",
                                                 u"mickey@mouse.com",
                                                 u"Mickey",
                                                 u"Mouse")
            request = Request.blank('/')
            event = component.getMultiAdapter(
                ('disneyProvider', user, user_assertion_info, request),
                ISAMLUserAuthenticatedEvent
            )

            saml_response = fudge.Fake('saml_response')
            saml_response.provides('id').returns(u"fakesamlid")
            saml_response.provides('session_id').returns(u"fakesamlsessionid")
            saml_response.provides('session_info').returns({u"issuer": u"testIssuer"})
            event.saml_response = saml_response

            self.registerComponents()

            #######
            # Test
            notify(event)

            #######
            # Verify
            expected_info = TestSAMLProviderUserInfo(user_assertion_info)
            actual_info = ISAMLIDPUserInfoBindings(user)['disneyProvider']
            assert_that(actual_info.__dict__,
                        has_entries(expected_info.__dict__))

    def registerComponents(self):
        component.getSiteManager().registerAdapter(TestSAMLUserAssertionInfo,
                                                   (dict,),
                                                   ISAMLUserAssertionInfo,
                                                   'disneyProvider')
        component.getSiteManager().registerAdapter(TestSAMLProviderUserInfo,
                                                   (ISAMLUserAssertionInfo,),
                                                   ISAMLProviderUserInfo,
                                                   'disneyProvider')
