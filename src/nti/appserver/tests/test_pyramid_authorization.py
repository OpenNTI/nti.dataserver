#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import same_instance

from nti.testing.matchers import is_true
from nti.testing.matchers import is_false

from zope import interface

import pyramid.security
import pyramid.interfaces

from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver import authorization_acl as auth_acl

from nti.appserver.pyramid_authorization import is_readable
from nti.appserver.pyramid_authorization import is_writable
from nti.appserver.pyramid_authorization import ZopeACLAuthorizationPolicy

from nti.appserver.tests import ConfiguringTestBase

class TestPyramidAuthorization(ConfiguringTestBase):  # Not shared, we muck with the registry a lot

	def setUp(self):
		super(TestPyramidAuthorization, self).setUp()

		@interface.implementer(pyramid.interfaces.IAuthenticationPolicy)
		class AuthPolicy(object):
			userid = 'jason.madden@nextthought.com'

			def authenticated_userid(self, request):
				return self.userid

			def effective_principals(self, request):
				return (self.authenticated_userid(request),
						nti_interfaces.AUTHENTICATED_GROUP_NAME)

		self.auth_policy = AuthPolicy()
		self.request.registry.registerUtility(self.auth_policy)
		self.policy = ZopeACLAuthorizationPolicy()
		self.request.registry.registerUtility(self.policy)

	def tearDown(self):
		super(TestPyramidAuthorization, self).tearDown()
		self.request.registry.unregisterUtility(self.auth_policy)
		self.request.registry.unregisterUtility(self.policy)

	def test_policy(self):

		class Parent(object):
			pass

		class Child(object):
			def __init__(self):
				self.__parent__ = Parent()

		assert_that(Child(), self.doesnt_have_permission('edit'))

		# But with an ACL provider for the parent, we do
		class Provider(object):

			def __init__(self, context):
				pass

			@property
			def __acl__(self):
				return  ((pyramid.security.Allow,
						  pyramid.security.Authenticated,
						  pyramid.security.ALL_PERMISSIONS),)

		self.request.registry.registerAdapter(Provider, (Parent,),
											  nti_interfaces.IACLProvider)
		# Ensure we provided what we think we provided
		assert_that(auth_acl.ACL(Child().__parent__, is_(Provider(None).__acl__)))

		assert_that(Child(), bool(self.has_permission('edit')))

	def test_caching(self):

		class WithACL(object):
			__acl__ = ((pyramid.security.Allow,
						self.auth_policy.userid,
						pyramid.security.ALL_PERMISSIONS),)

		withacl = WithACL()
		assert_that(is_readable(withacl, self.request), is_true())
		assert_that(is_writable(withacl, self.request), is_true())
		assert_that(is_readable(withacl, self.request),
					is_(same_instance(is_readable(withacl, self.request))))

		# Change the userid and get a different answer
		self.auth_policy.userid = 'foo'
		assert_that(is_readable(withacl, self.request), is_false())
		assert_that(is_writable(withacl, self.request), is_false())
		assert_that(is_readable(withacl, self.request),
					is_(same_instance(is_readable(withacl, self.request))))
