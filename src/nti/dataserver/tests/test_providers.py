#!/usr/bin/env python2.7
#pylint: disable=R0904

import unittest
from hamcrest import assert_that, has_length, contains_string, is_, same_instance, is_not, has_item
from nti.dataserver.tests import has_attr, provides
from zope.interface.verify import verifyObject
from zope import component

import nti.dataserver.interfaces as nti_interfaces
from nti.dataserver.interfaces import IPrincipal
from nti.dataserver import authorization as auth
from nti.dataserver.authorization_acl import ace_allowing, ace_denying
from nti.dataserver.providers import Provider


import mock_dataserver

class TestProvider(mock_dataserver.ConfiguringTestBase):

	@mock_dataserver.WithMockDSTrans
	def test_provider_iface(self):
		provider = Provider.create_provider( self.ds, username="OU" )
		assert_that( provider, provides( nti_interfaces.IProviderOrganization ) )
		verifyObject( nti_interfaces.IProviderOrganization, provider )

	@mock_dataserver.WithMockDSTrans
	def test_provider_acl(self):
		provider = Provider.create_provider( self.ds, username="OU" )

		acl_prov = nti_interfaces.IACLProvider( provider )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		# Three entries, one for each pseudo-role (plus, currently, one to deny)
		# (Obviously, this will change)
		acl = acl_prov.__acl__
		assert_that( acl, has_length( 4 ) )

		assert_that( acl, has_item( ace_allowing( IPrincipal( "role:OU.Admin" ), nti_interfaces.ALL_PERMISSIONS ) ) )
		assert_that( acl, has_item( ace_allowing( IPrincipal( "role:OU.Instructor" ), auth.ACT_READ ) ) )
		assert_that( acl, has_item( ace_allowing( IPrincipal( "role:OU.Student" ), auth.ACT_READ ) ) )
		assert_that( acl, has_item( ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS ) ) )
