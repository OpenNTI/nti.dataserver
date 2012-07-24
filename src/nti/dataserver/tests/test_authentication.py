#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_in

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authentication
from nti.dataserver import users

from nti.tests import verifiably_provides
from pyramid.testing import DummySecurityPolicy
from nti.dataserver.tests import mock_dataserver

def test_delegating_provides():

	assert_that( authentication.DelegatingImpersonatedAuthenticationPolicy( DummySecurityPolicy( '' ) ),
				 verifiably_provides( nti_interfaces.IImpersonatedAuthenticationPolicy ) )

def test_effective_prins_no_username():
	assert_that( authentication.effective_principals( '' ), is_( () ) )


class TestPrincipals(mock_dataserver.ConfiguringTestBase):


	@mock_dataserver.WithMockDSTrans
	def test_effective_principals(self):
		assert_that( authentication.effective_principals( None ), is_( () ) )
		u = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		community = users.Community( "Foobar" )
		self.ds.root['users']['Foobar'] = community
		u.join_community( community )

		with_u = authentication.effective_principals( u )
		by_name = authentication.effective_principals( u.username )

		assert_that( with_u, is_( by_name ) )
		# Domain
		assert_that( nti_interfaces.IPrincipal( 'nextthought.com' ),
					 is_in( with_u ) )
		# user
		assert_that( nti_interfaces.IPrincipal( u ),
					 is_in( with_u ) )

		# Community
		assert_that( nti_interfaces.IPrincipal( community ),
					 is_in( with_u ) )
