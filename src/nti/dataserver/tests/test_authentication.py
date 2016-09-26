#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import empty
from hamcrest import is_
from hamcrest import is_in
import unittest

import fudge

from fudge.inspector import arg

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authentication
from nti.dataserver import users

from nti.testing.matchers import is_false
from nti.testing.matchers import validly_provides as verifiably_provides

from pyramid.testing import DummySecurityPolicy
from nti.dataserver.tests import mock_dataserver

class TestMisc(unittest.TestCase):
	def test_delegating_provides(self):

		assert_that( authentication.DelegatingImpersonatedAuthenticationPolicy( DummySecurityPolicy( '' ) ),
					 verifiably_provides( nti_interfaces.IImpersonatedAuthenticationPolicy ) )

	def test_effective_prins_no_username(self):
		assert_that( authentication.effective_principals( '' ), empty() )


class TestPrincipals(mock_dataserver.DataserverLayerTest):

	@mock_dataserver.WithMockDSTrans
	def test_effective_principals(self):
		assert_that( authentication.effective_principals( None ), empty() )
		assert_that( authentication.effective_principals( None ), is_false() )
		u = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		community = users.Community( "Foobar" )
		self.ds.root['users']['Foobar'] = community
		u.record_dynamic_membership( community )

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


	@mock_dataserver.WithMockDSTrans
	def test_for_everyone_string(self):
		assert_that( authentication.effective_principals( None ), empty() )
		assert_that( authentication.effective_principals( None ), is_false() )
		u = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )

		with_u = authentication.effective_principals( u )

		#pyramid security defines it's everyone group as system.Everyone and the
		#our subsequent ACE_DENY_ALL ACE uses that identifier.  Ensure
		#that is in our effective principals so that it hits correctly.

		assert_that('system.Everyone', is_in( with_u ))
		assert_that(nti_interfaces.IPrincipal('system.Everyone'), is_in( with_u ))