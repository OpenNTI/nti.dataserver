#!/usr/bin/env python2.7

#pylint: disable=R0904,W0402
from hamcrest import assert_that, has_length, contains_string, is_, same_instance, is_not, is_in
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

	def test_sorting(self):
		a = nti_interfaces.IPrincipal('a')
		b = nti_interfaces.IPrincipal('b')
		c = nti_interfaces.IPrincipal('c')
		d = nti_interfaces.IPrincipal('d')

		unsorted = [d, b, a, c]
		srtd = sorted(unsorted)
		assert_that( srtd, is_( [a, b, c, d] ) )


	def test_user_adapts( self ):
		u = users.User( 'sjohnson@nextthought.com', 't' )
		iprin = nti_interfaces.IPrincipal( u )
		assert_that( iprin, verifiably_provides( nti_interfaces.IPrincipal ) )
		assert_that( iprin.id, is_( u.username ) )
		assert_that( iprin.description, is_( u.username ) )
		assert_that( iprin.title, is_( u.username ) )
		assert_that( repr(iprin), is_("_UserPrincipal('sjohnson@nextthought.com')") )
		assert_that( str(iprin), is_('sjohnson@nextthought.com') )

	@mock_dataserver.WithMockDSTrans
	def test_effective_principals(self):
		assert_that( nauth.effective_principals( None ), is_( () ) )
		u = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )

		with_u = nauth.effective_principals( u )
		by_name = nauth.effective_principals( u.username )

		assert_that( with_u, is_( by_name ) )
		# Domain
		assert_that( nti_interfaces.IPrincipal( 'nextthought.com' ),
					 is_in( with_u ) )
		# user
		assert_that( nti_interfaces.IPrincipal( u ),
					 is_in( with_u ) )



def test_permission_methods():
	assert_that( nauth.ACT_CREATE, is_( Permission( nauth.ACT_CREATE.id ) ) )
	assert_that( nauth.ACT_CREATE, is_not( None ) )
	assert_that( str(nauth.ACT_CREATE), is_( nauth.ACT_CREATE.id ) )
	assert_that( repr(nauth.ACT_CREATE), is_( "Permission('nti.actions.create','','')" ) )
