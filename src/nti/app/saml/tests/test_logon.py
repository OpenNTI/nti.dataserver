#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import equal_to
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_properties

import gc

import fudge

from saml2.saml import NAMEID_FORMAT_PERSISTENT

from persistent import Persistent

from pyramid.interfaces import IRequest

from pyramid.request import Request

from zope.interface.registry import Components

from zope.interface.adapter import AdapterRegistry
from zope.interface.adapter import BaseAdapterRegistry

from zope import component
from zope import interface

from zope.component.hooks import site

from nti.app.saml.interfaces import ISAMLClient
from nti.app.saml.interfaces import ISAMLACSLinkProvider
from nti.app.saml.interfaces import ISAMLUserAssertionInfo
from nti.app.saml.interfaces import ISAMLUserAuthenticatedEvent

from nti.app.saml.logon import acs_view

from nti.dataserver.interfaces import IUser

from nti.dataserver.users.users import User

from nti.site.transient import TrivialSite

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


@interface.implementer(ISAMLUserAuthenticatedEvent)
class TestSAMLUserAuthenticatedEvent(object):

	def __init__(self, idp_id, user, user_info, request):
		self.user = user
		self.object = user
		self.idp_id = idp_id
		self.request = request
		self.user_info = user_info


class IsolatedAdapterRegistry(AdapterRegistry):

	def _setBases(self, bases):
		# Avoid using _addSubregistry to avoid leaving references around
		# (and because it might not exist!)
		BaseAdapterRegistry._setBases(self, bases)


class IsolatedComponents(Persistent, Components):

	def _init_registries(self):
		self.adapters = IsolatedAdapterRegistry()
		self.utilities = IsolatedAdapterRegistry()

	@property
	def __parent__(self):
		# So that IConnection(site_manager) can work.
		return self.__bases__[0]


class TestACSLinkProvider(ApplicationLayerTest):

	@WithMockDSTrans
	def test_acs_location(self):
		request = Request.blank('/')
		link_provider = ISAMLACSLinkProvider(request)
		assert_that(link_provider, not_none())
		link = link_provider.acs_link(request)
		assert_that(link, is_('http://localhost/dataserver2/saml/@@acs'))


class TestEvents(ApplicationLayerTest):

	captured_event = None

	def setUp(self):
		self.captured_event = None

	def tearDown(self):
		self.captured_event = None
		# Clean up the weak refs to the Components object we created so they don't
		# destroy the world.
		gc.collect()

	@WithMockDSTrans
	@fudge.patch('nti.app.saml.logon._deal_with_external_account',
				 'nti.dataserver.users.users.User.get_entity')
	def test_user_creation_event(self, ext_acct_handler, get_entity):

		########
		# Setup
		with site(TrivialSite(IsolatedComponents('nti.app.saml.tests',
												 bases=(component.getSiteManager(),)))):
			sm = component.getSiteManager()
			assert isinstance(sm, Persistent)

			saml_response = fudge.Fake('saml_response')
			saml_response.provides('session_info').returns({"issuer":"testIssuer"})
			saml_response.provides('id').returns("fakesamlid")
			saml_response.provides('session_id').returns("fakesamlsessionid")

			saml_client = fudge.Fake('saml_client')
			saml_client.provides('process_saml_acs_request').returns((saml_response,None,None,None))
			sm.registerUtility(saml_client, ISAMLClient)

			nameid = fudge.Fake('nameid').has_attr(name_format=NAMEID_FORMAT_PERSISTENT)
			user_info = fudge.Fake().has_attr(username=u'testUser',
											  nameid=nameid,
											  email=u'test@user.com',
											  firstname=u'test',
											  lastname=u'user',
											  realname=None)
			user_info_factory = fudge.Fake().is_callable().returns(user_info)
			interface.alsoProvides(user_info, ISAMLUserAssertionInfo)
			sm.registerAdapter(user_info_factory, required=(dict,),
							   provided=ISAMLUserAssertionInfo,
							   name="testIssuer")

			get_entity.is_callable().returns(None)

			user = User.create_user(username=u'testUser')
			ext_acct_handler.is_callable().returns(user)

			fake_handler = fudge.Fake('created_event_handler').is_callable().expects_call()

			self.captured_event = None
			@component.adapter(ISAMLUserAuthenticatedEvent)
			def user_creation_handler(event):
				self.captured_event = event
				return fake_handler(event)

			sm.registerHandler(user_creation_handler)

			sm.registerAdapter(TestSAMLUserAuthenticatedEvent,
							   [basestring, IUser, ISAMLUserAssertionInfo, IRequest])

			request = Request.blank('/')
			request.registry = sm

			#######
			# Test
			#
			acs_view(request)

			#######
			# Verify

			assert_that(self.captured_event, not_none())
			assert_that(self.captured_event, has_properties({"user":equal_to(user),
															 "request":equal_to(request),
															 "user_info":equal_to(user_info)}))

	@WithMockDSTrans
	@fudge.patch('nti.dataserver.users.users.User.get_entity',
				 'nti.app.saml.logon._validate_idp_nameid')
	def test_user_creation_event_existing_user(self, get_entity, fake_validate_nameid):
		fake_validate_nameid.is_callable().returns(True)
		with site(TrivialSite(IsolatedComponents('nti.app.saml.tests',
												 bases=(component.getSiteManager(),)))):
			########
			# Setup

			sm = component.getSiteManager()

			saml_response = fudge.Fake('saml_response')
			saml_response.provides('session_info').returns({"issuer":"testIssuer"})
			saml_response.provides('id').returns("fakesamlid")
			saml_response.provides('session_id').returns("fakesamlsessionid")

			saml_client = fudge.Fake('saml_client')
			saml_client.provides('process_saml_acs_request').returns(
				(saml_response,None,None,None)
			)
			sm.registerUtility(saml_client, ISAMLClient)

			nameid = fudge.Fake('nameid').has_attr(name_format=NAMEID_FORMAT_PERSISTENT)
			user_info = fudge.Fake().has_attr(username=u'testUser',
											  nameid=nameid,
											  email=u'test@user.com',
											  firstname=u'test',
											  lastname=u'user')
			user_info_factory = fudge.Fake().is_callable().returns(user_info)
			interface.alsoProvides(user_info, ISAMLUserAssertionInfo)
			sm.registerAdapter(user_info_factory, required=(dict,),
							   provided=ISAMLUserAssertionInfo, name="testIssuer")

			user = User.create_user(username='testUser')
			get_entity.is_callable().returns(user)

			fake_handler = fudge.Fake('created_event_handler').is_callable().expects_call()

			self.captured_event = None
			@component.adapter(ISAMLUserAuthenticatedEvent)
			def user_creation_handler(event):
				self.captured_event = event
				return fake_handler(event)

			sm.registerHandler(user_creation_handler)

			sm.registerAdapter(TestSAMLUserAuthenticatedEvent,
							  [basestring, IUser, ISAMLUserAssertionInfo, IRequest])

			request = Request.blank('/')
			request.registry = sm

			#######
			# Test
			#
			acs_view(request)

			#######
			# Verify

			assert_that(self.captured_event, not_none())
			assert_that(self.captured_event, has_properties({"user":equal_to(user),
															 "request":equal_to(request),
															 "user_info":equal_to(user_info)}))
