#!/usr/bin/env python2.7

import unittest
from hamcrest import assert_that, has_length, contains_string, is_, same_instance, is_not
from nti.dataserver.tests import has_attr, provides
from nti.tests import verifiably_provides
from zope.interface.verify import verifyObject
from zope import component

from zope.security.permission import Permission
import nti.dataserver.authorization as nauth
import nti.dataserver.users as users
import nti.dataserver.interfaces as nti_interfaces

import mock_dataserver

class TestPGM(mock_dataserver.ConfiguringTestBase):

	def test_user_adapts( self ):
		u = users.User( 'sjohnson@nextthought.com', 't' )
		pgm = nti_interfaces.IGroupMember( u )

		assert_that( u, has_attr( '__annotations__' ) )
		assert_that( u.__annotations__, has_length( 1 ) )
		assert_that( list(u.__annotations__.keys())[0], contains_string( pgm.__class__.__name__ ) )

		verifyObject( nti_interfaces.IGroupMember, pgm )

		assert_that( list(pgm.groups), is_([]) )

class TestPrincipals(mock_dataserver.ConfiguringTestBase):

	def test_string_adapts( self ):
		# no-name
		iprin = nti_interfaces.IPrincipal( 'foo@bar' )
		assert_that( iprin, provides( nti_interfaces.IPrincipal ) )
		verifyObject( nti_interfaces.IPrincipal, iprin )

		# named system, as component
		assert_that( component.getAdapter( nti_interfaces.SYSTEM_USER_NAME,
										   nti_interfaces.IPrincipal,
										   name=nti_interfaces.SYSTEM_USER_NAME ),
					 is_( same_instance( nti_interfaces.system_user ) ) )
		# system without name, as interface
		assert_that( nti_interfaces.IPrincipal( nti_interfaces.SYSTEM_USER_NAME ),
					 is_( same_instance( nti_interfaces.system_user ) ) )
		# everyone
		assert_that( nti_interfaces.IPrincipal( 'system.Everyone' ),
					 provides( nti_interfaces.IGroup ) )
		# everyone authenticated
		assert_that( nti_interfaces.IPrincipal( 'system.Authenticated' ),
					 provides( nti_interfaces.IGroup ) )
		assert_that( nti_interfaces.IPrincipal( 'system.Authenticated' ),
					 is_not( nti_interfaces.IPrincipal( 'system.Everyone' ) ) )


	def test_user_adapts( self ):
		u = users.User( 'sjohnson@nextthought.com', 't' )
		iprin = nti_interfaces.IPrincipal( u )
		assert_that( iprin, verifiably_provides( nti_interfaces.IPrincipal ) )
		assert_that( iprin.id, is_( u.username ) )
		assert_that( iprin.description, is_( u.username ) )
		assert_that( iprin.title, is_( u.username ) )



def test_permission_methods():
	assert_that( nauth.ACT_CREATE, is_( Permission( nauth.ACT_CREATE.id ) ) )
	assert_that( nauth.ACT_CREATE, is_not( None ) )
	assert_that( str(nauth.ACT_CREATE), is_( nauth.ACT_CREATE.id ) )
	assert_that( repr(nauth.ACT_CREATE), is_( "Permission('nti.actions.create','','')" ) )
