#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

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

from zope.event import notify

from zope import component
from zope import interface

from zope.component.hooks import site

from pyramid.request import Request

from nti.app.saml.events import SAMLUserCreatedEvent

from nti.app.saml.events import _user_created
from nti.app.saml.events import _user_removed

from nti.app.saml.interfaces import ISAMLNameId
from nti.app.saml.interfaces import ISAMLUserAssertionInfo
from nti.app.saml.interfaces import ISAMLUserAuthenticatedEvent

from nti.dataserver.saml.interfaces import ISAMLProviderUserInfo
from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings

from nti.dataserver.users import users

from nti.schema.eqhash import EqHash

from nti.site.transient import TrivialSite

from nti.app.saml.tests.test_logon import IsolatedComponents

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


@interface.implementer(ISAMLUserAssertionInfo)
class TestSAMLUserAssertionInfo:

    def __init__(self, saml_response):
        for k, v in saml_response.items():
            setattr(self, k, v)


# ITestSAMLProviderUserInfo


@EqHash('provider_id')
@interface.implementer(ISAMLProviderUserInfo)
class TestSAMLProviderUserInfo:

    def __init__(self, user_assertion_info):
        self.provider_id = user_assertion_info.provider_id
        self.username = user_assertion_info.username
        self.nameid = user_assertion_info.nameid
        self.email = user_assertion_info.email
        self.firstname = user_assertion_info.firstname
        self.lastname = user_assertion_info.lastname


def assertion_info(provider_id, username, email, firstname, lastname):
    name_id = fudge.Fake('name_id').has_attr(nameid=u"testNameId",
                                             name_format=NAMEID_FORMAT_PERSISTENT,
                                             name_qualifier=provider_id,
                                             sp_name_qualifier=None)
    interface.alsoProvides(name_id, ISAMLNameId)
    return TestSAMLUserAssertionInfo({u"provider_id": provider_id,
                                      u"username": username,
                                      u"nameid": name_id,
                                      u"email": email,
                                      u"firstname": firstname,
                                      u"lastname": lastname,
                                      u"realname": None})


class TestEvents(ApplicationLayerTest):

    @WithMockDSTrans
    def test_interfaces(self):
        ########
        # Setup
        user = users.User.create_user(username=u'testUser')
        request = Request.blank('/')

        #######
        # Test
        user_assertion_info = assertion_info(u"pid1",
                                             u"bradley@maycomb.com",
                                             u"bradley@maycomb.com",
                                             u"Boo",
                                             u"Radley")
        user_created_event = SAMLUserCreatedEvent(u'harperProvider',
                                                  user,
                                                  user_assertion_info,
                                                  request)

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
            user = users.User.create_user(username='testUser')
            user_assertion_info = assertion_info(u"pid2",
                                                 u"mickey@mouse.com",
                                                 u"mickey@mouse.com",
                                                 u"Mickey",
                                                 u"Mouse")
            request = Request.blank('/')
            event = SAMLUserCreatedEvent(u'disneyProvider',
                                         user,
                                         user_assertion_info,
                                         request)

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
            user = users.User.create_user(username='testUser')
            user_assertion_info = assertion_info(u"pid2",
                                                 u"mickey@mouse.com",
                                                 u"mickey@mouse.com",
                                                 u"Mickey",
                                                 u"Mouse")
            request = Request.blank('/')
            event = SAMLUserCreatedEvent('disneyProvider',
                                         user,
                                         user_assertion_info,
                                         request)

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
            #

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
        with mock_dataserver.mock_db_trans(self.ds):
            ########
            # Setup
            user = users.User.create_user(username='testUser')
            user_assertion_info = assertion_info(u"pid2",
                                                 u"mickey@mouse.com",
                                                 u"mickey@mouse.com",
                                                 u"Mickey",
                                                 u"Mouse")
            request = Request.blank('/')
            event = component.getMultiAdapter(('disneyProvider', user, user_assertion_info, request),
                                              ISAMLUserAuthenticatedEvent)

            #######
            # Test
            #
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
            user = users.User.create_user(username='testUser')
            user_assertion_info = assertion_info(u"pid2",
                                                 u"mickey@mouse.com",
                                                 u"mickey@mouse.com",
                                                 u"Mickey",
                                                 u"Mouse")
            request = Request.blank('/')
            event = component.getMultiAdapter(('disneyProvider', user, user_assertion_info, request),
                                              ISAMLUserAuthenticatedEvent)

            self.registerComponents()

            #######
            # Test
            #
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
