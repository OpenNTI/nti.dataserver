#!/usr/bin/env python2.7
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, ends_with,
					  has_entry, has_length, has_key, is_not)
from hamcrest.library import has_property
from nti.appserver.logon import (ping, handshake,password_logon)

from nti.appserver.tests import ConfiguringTestBase
from pyramid.threadlocal import get_current_request
import pyramid.testing
import pyramid.httpexceptions as hexc
import persistent
import UserList

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
#from nti.tests import provides

from zope import interface
import nti.dataserver.interfaces as nti_interfaces

from nti.dataserver import datastructures

class DummyView(object):
	response = "Response"
	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		return self.response

class TestLogon(ConfiguringTestBase):

	def test_unathenticated_ping(self):
		"An unauthenticated ping returns one link, to the handshake."
		self.config.add_route( name='logon.handshake', pattern='/dataserver2/handshake' )
		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 1 ) ) )
		assert_that( result.links[0].target, ends_with( '/dataserver2/handshake' ) )
		datastructures.to_external_representation( result, datastructures.EXT_FORMAT_JSON, name='wsgi' )

	def test_authenticated_ping(self):
		"An authenticated ping returns two links, to the handshake and the root"
		self.config.add_route( name='user.root.service', pattern='/dataserver2{_:/?}' )
		self.config.add_route( name='logon.handshake', pattern='/dataserver2/handshake' )
		self.config.add_route( name='logon.logout', pattern='/dataserver2/logon.logout' )
		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'
		get_current_request().registry.registerUtility( Policy() )
		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 3 ) ) )
		assert_that( result.links[0].target, ends_with( '/dataserver2/handshake' ) )
		assert_that( result.links[1].target, ends_with( '/dataserver2' ) )

	@WithMockDSTrans
	def test_authenticated_handshake(self):
		"An authenticated handshake returns two links, to the logon and the root"
		self.config.add_route( name='user.root.service', pattern='/dataserver2{_:/?}' )
		self.config.add_route( name='logon.handshake', pattern='/dataserver2/handshake' )
		self.config.add_route( name='logon.nti.password', pattern='/dataserver2/logon.password' )
		self.config.add_route( name='logon.google', pattern='/dataserver2/logon.google' )
		self.config.add_route( name='logon.logout', pattern='/dataserver2/logon.logout' )
		self.config.add_route( name='logon.facebook.oauth1', pattern='/dataserver2/logon.facebook.1' )

		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'
		get_current_request().registry.registerUtility( Policy() )
		get_current_request().params['username'] = 'jason.madden@nextthought.com'
		result = handshake( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 4 ) ) )
		assert_that( result.links[0].target, is_( '/dataserver2/logon.google' ) )
		assert_that( result.links[1].target, is_( '/dataserver2/logon.facebook.1' ) )
		assert_that( result.links[2].target, is_( '/dataserver2' ) )
		assert_that( result.links[3].target, is_( '/dataserver2/logon.logout' ) )

	def test_password_logon_failed(self):
		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def forget( self, request ):
				return [("Policy", "Me")]
			def authenticated_userid( self, request ): return None
		get_current_request().registry.registerUtility( Policy() )
		result = password_logon( get_current_request() )
		assert_that( result, is_( hexc.HTTPUnauthorized ) )
		assert_that( result.headers, has_entry( "Policy", "Me" ) )

        # Or a redirect
		get_current_request().params['failure'] = '/the/url/to/go/to'
		result = password_logon( get_current_request() )
		assert_that( result, is_( hexc.HTTPSeeOther ) )
		assert_that( result.headers, has_entry( "Policy", "Me" ) )
		assert_that( result, has_property( 'location', '/the/url/to/go/to' ) )

	def test_password_logon_success(self):
		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def remember( self, request, who ):
				return [("Policy", who)]
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'
		get_current_request().registry.registerUtility( Policy() )
		result = password_logon( get_current_request() )
		assert_that( result, is_( hexc.HTTPNoContent ) )
		assert_that( result.headers, has_entry( "Policy", 'jason.madden@nextthought.com' ) )

        # Or a redirect
		get_current_request().params['success'] = '/the/url/to/go/to'
		result = password_logon( get_current_request() )
		assert_that( result, is_( hexc.HTTPSeeOther ) )
		assert_that( result.headers, has_entry( "Policy", 'jason.madden@nextthought.com') )
		assert_that( result, has_property( 'location', '/the/url/to/go/to' ) )
