#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import has_properties
from hamcrest import none
from hamcrest import not_none

from nti.app.saml.interfaces import ISAMLClient
from nti.app.saml.interfaces import ISAMLUserAssertionInfo
from nti.app.saml.interfaces import ISAMLUserCreatedEvent

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.application_webtest import ApplicationTestLayer

from nti.appserver.policies.sites import BASEADULT

from nti.dataserver.interfaces import IUser

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import users

from pyramid.interfaces import IRequest

from pyramid.request import Request

from saml2.saml import NAMEID_FORMAT_PERSISTENT

from z3c.baseregistry.baseregistry import BaseComponents

from zope import component
from zope import interface

from zope.component.interfaces import IComponents

from ..logon import acs_view

_MYSITE = BaseComponents(BASEADULT, name='nti.app.saml.tests', bases=(BASEADULT,))

@interface.implementer(ISAMLUserCreatedEvent)
class TestSAMLUserCreatedEvent:
	def __init__(self, idp_id, user, user_info, request):
		self.idp_id = idp_id
		self.user = user
		self.object = user
		self.user_info = user_info
		self.request = request


class TestEvents(ApplicationLayerTest):
	
	layer = ApplicationTestLayer

	@WithMockDSTrans
	@fudge.patch('nti.app.saml.logon._deal_with_external_account', 'nti.dataserver.users.users.User.get_entity')
	def test_user_creation_event(self, ext_acct_handler, get_entity):
		
		########
		# Setup
		
		component.getGlobalSiteManager().registerUtility(_MYSITE, IComponents, name='nti.app.saml.tests')
		with mock_dataserver.mock_db_trans(self.ds, site_name='nti.app.saml.tests'):
			sm = component.getSiteManager();
			
			saml_client = fudge.Fake('saml_client')
			saml_client.provides('process_saml_acs_request').returns(({"issuer":"testIssuer"},None,None,None))
			sm.registerUtility(saml_client, ISAMLClient)
	
			nameid = fudge.Fake('nameid').has_attr(name_format=NAMEID_FORMAT_PERSISTENT)
			user_info = fudge.Fake().has_attr(username='testUser', nameid=nameid, email='test@user.com', firstname='test', lastname='user')
			user_info_factory = fudge.Fake().is_callable().returns(user_info)
			interface.alsoProvides(user_info, ISAMLUserAssertionInfo)
			sm.registerAdapter(user_info_factory, required=(dict,), provided=ISAMLUserAssertionInfo, name="testIssuer")
			
			get_entity.is_callable().returns(None)
			
			user = users.User.create_user(username='testUser')
			ext_acct_handler.is_callable().returns(user)
			
			fake_handler = fudge.Fake('created_event_handler').is_callable().expects_call()
	
			self.captured_event = None
			@component.adapter(ISAMLUserCreatedEvent)
			def user_creation_handler(event):
				self.captured_event = event
				return fake_handler(event)
	
			sm.registerHandler(user_creation_handler)
	
			sm.registerAdapter(TestSAMLUserCreatedEvent, [basestring, IUser, ISAMLUserAssertionInfo, IRequest])
	
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
	@fudge.patch('nti.dataserver.users.users.User.get_entity')
	def test_user_creation_event_existing_user(self, get_entity):
		
		component.getGlobalSiteManager().registerUtility(_MYSITE, IComponents, name='nti.app.saml.tests')
		with mock_dataserver.mock_db_trans(self.ds, site_name='nti.app.saml.tests'):
			########
			# Setup
			
			sm = component.getSiteManager();
			
			saml_client = fudge.Fake('saml_client')
			saml_client.provides('process_saml_acs_request').returns(({"issuer":"testIssuer"},None,None,None))
			sm.registerUtility(saml_client, ISAMLClient)
	
			nameid = fudge.Fake('nameid').has_attr(name_format=NAMEID_FORMAT_PERSISTENT)
			user_info = fudge.Fake().has_attr(username='testUser', nameid=nameid, email='test@user.com', firstname='test', lastname='user')
			user_info_factory = fudge.Fake().is_callable().returns(user_info)
			interface.alsoProvides(user_info, ISAMLUserAssertionInfo)
			sm.registerAdapter(user_info_factory, required=(dict,), provided=ISAMLUserAssertionInfo, name="testIssuer")
			
			user = users.User.create_user(username='testUser')
			get_entity.is_callable().returns(user)
			
			
			self.captured_event = None
			@component.adapter(ISAMLUserCreatedEvent)
			def user_creation_handler(event):
				self.captured_event = event
	
			sm.registerHandler(user_creation_handler)
	
			sm.registerAdapter(TestSAMLUserCreatedEvent, [basestring, IUser, ISAMLUserAssertionInfo, IRequest])
	
			request = Request.blank('/')
			request.registry = sm
	
			#######
			# Test
			#
			acs_view(request)
			
			#######
			# Verify
			
			assert_that(self.captured_event, none())
