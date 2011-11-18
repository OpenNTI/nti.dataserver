#!/usr/bin/env python2.7

import unittest
from hamcrest import assert_that, has_length, contains_string
from nti.dataserver.tests import has_attr
from zope.interface.verify import verifyObject

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

