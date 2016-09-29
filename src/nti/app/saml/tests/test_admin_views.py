#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import interface

from hamcrest import assert_that
from hamcrest import ends_with
from hamcrest import has_entries
from hamcrest import starts_with

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.application_webtest import ApplicationTestLayer

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings

from nti.dataserver.tests import mock_dataserver

from nti.schema.schema import SchemaConfigured

from persistent.persistence import Persistent

from .interfaces import ITestSAMLProviderUserInfo

@interface.implementer(ITestSAMLProviderUserInfo)		
class TestProviderInfo(SchemaConfigured, Persistent):
	test_id = 'testID1'
	mimeType = mime_type = 'application/vnd.nextthought.saml.testprovideruserinfo'

class TestViews(ApplicationLayerTest):
	
	layer = ApplicationTestLayer
	layer.set_up_packages = ('nti.app.saml.tests',)

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_provider_info_view_no_user(self):
		########
		# Setup
		getUrl = "/dataserver2/saml/@@GetProviderUserInfo"
		
		username = 'bobby.hagen@nextthought.com'
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(username=username)
		
		extra_environ = self._make_extra_environ(username=username)

		#######
		# Test
		response = self.testapp.get(getUrl,
						{},
						status=422,
						extra_environ=extra_environ)

		#######
		# Verify
		
		assert_that(str(response), ends_with('Must specify a username.'))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_provider_info_view_no_entity_id(self):
		########
		# Setup
		getUrl = "/dataserver2/saml/@@GetProviderUserInfo"
		
		username = b'bobby.hagen@nextthought.com'
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(username=username)
		
		extra_environ = self._make_extra_environ(username=username)

		#######
		# Test
		response = self.testapp.get(getUrl,
						{'user':username},
						status=422,
						extra_environ=extra_environ)

		#######
		# Verify
		
		assert_that(str(response), ends_with('Must specify entity_id.'))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_provider_info_view_user_not_found(self):
		########
		# Setup
		getUrl = "/dataserver2/saml/@@GetProviderUserInfo"
		
		username = b'bobby.hagen@nextthought.com'
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(username=username)
		
		extra_environ = self._make_extra_environ(username=username)

		#######
		# Test
		response = self.testapp.get(getUrl,
						{'user':'the.donald@trump.com', 'entity_id':'test_entity_id'},
						status=422,
						extra_environ=extra_environ)

		#######
		# Verify
		
		assert_that(str(response), ends_with('User not found.'))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_provider_info_view_unauthorized(self):

		########
		# Setup
		getUrl = "/dataserver2/saml/@@GetProviderUserInfo"

		username = b'bobby.hagen@test.com'
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(username=username)

		extra_environ = self._make_extra_environ(username=username)

		#######
		# Test
		self.testapp.get(getUrl,
						 {'user':username, 'entity_id':'test_entity_id'},
						 status=403, # FORBIDDEN!!!
						 extra_environ=extra_environ)

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_provider_info_view(self):

		########
		# Setup
		getUrl = "/dataserver2/saml/@@GetProviderUserInfo"

		username = b'bobby.hagen@nextthought.com'
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user(username=username)
			ISAMLIDPUserInfoBindings(user)['test_entity_id'] = TestProviderInfo()

		extra_environ = self._make_extra_environ(username=username)

		#######
		# Test
		response = self.testapp.get(getUrl,
						{'user':username, 'entity_id':'test_entity_id'},
						status=200,
						extra_environ=extra_environ)

		#######
		# Verify
		
# 		assert_that(str(response), ends_with('Must specify entity_id.'))
		result = response.json_body
		assert_that(result,
					has_entries({'href': starts_with(getUrl),
								 'Class': 'TestProviderInfo',
								 'test_id': 'testID1',
								 'MimeType': 'application/vnd.nextthought.saml.testprovideruserinfo'
								 }))
