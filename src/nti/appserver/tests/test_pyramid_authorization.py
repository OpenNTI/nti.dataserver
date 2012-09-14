#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_

from nti.appserver.tests import ConfiguringTestBase

from nti.appserver.pyramid_authorization import ACLAuthorizationPolicy

from nti.dataserver import authorization_acl as auth_acl
import pyramid.security
import pyramid.interfaces
from nti.dataserver import interfaces as nti_interfaces
from zope import interface

class TestPyramidAuthorization(ConfiguringTestBase):

	def test_policy(self):
		class AuthPolicy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'
			def effective_principals( self, request ):
				return [self.authenticated_userid(request), nti_interfaces.AUTHENTICATED_GROUP_NAME]

		self.request.registry.registerUtility( AuthPolicy() )
		self.request.registry.registerUtility( ACLAuthorizationPolicy() )

		class Parent(object): pass
		class Child(object):
			def __init__(self):
				self.__parent__ = Parent()


		assert_that( Child(), self.doesnt_have_permission( 'edit' ) )

		# But with an ACL provider for the parent, we do
		class Provider(object):
			def __init__( self, context ): pass

			@property
			def __acl__( self ):
				return  ( (pyramid.security.Allow, pyramid.security.Authenticated, pyramid.security.ALL_PERMISSIONS), )

		self.request.registry.registerAdapter( Provider, (Parent,), nti_interfaces.IACLProvider )
		# Ensure we provided what we think we provided
		assert_that( auth_acl.ACL( Child().__parent__, is_( Provider(None).__acl__ ) ) )

		assert_that( Child(), self.has_permission( 'edit' ) )
