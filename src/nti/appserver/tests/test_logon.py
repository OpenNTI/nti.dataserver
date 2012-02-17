#!/usr/bin/env python2.7
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, ends_with,
					  has_entry, has_length, has_key, is_not, has_item,
					  same_instance, none, greater_than_or_equal_to)
from hamcrest.library import has_property
from nti.tests import provides
from zope import component
from zope.component import eventtesting, provideHandler

from nti.appserver import logon
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
from nti.dataserver import users

class DummyView(object):
	response = "Response"
	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		return self.response

class TestLogon(ConfiguringTestBase):

	def setUp(self):
		super(TestLogon,self).setUp()
		eventtesting.clearEvents()
		del _user_added_events[:]

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

	@WithMockDSTrans
	def test_create_from_external( self ):
		component.provideHandler( eventtesting.events.append, (None,) )
		component.provideHandler( _handle_user_add_event )
		user = logon._deal_with_external_account( get_current_request(),
												  "Jason",
												  "Madden",
												  "jason.madden@nextthought.com",
												  "http://example.com",
												  nti_interfaces.IOpenIdUser,
												  users.OpenIdUser )
		assert_that( user, provides( nti_interfaces.IOpenIdUser ) )
		assert_that( user, is_( users.OpenIdUser ) )
		assert_that( user, has_property( 'identity_url', 'http://example.com' ) )

		# The creation of this user caused events to fire
		assert_that( eventtesting.getEvents(), has_length( greater_than_or_equal_to( 1 ) ) )
		assert_that( _user_added_events, has_length( 1 ) )
		assert_that( _user_added_events[0][0], is_( same_instance( user ) ) )
		assert_that( _user_added_events[0][1], has_property( 'oldParent', none() ) )

		# Can also auth as facebook
		fb_user = logon._deal_with_external_account( get_current_request(),
													 "Jason",
													 "Madden",
													 "jason.madden@nextthought.com",
													 "http://facebook.com",
													 nti_interfaces.IFacebookUser,
													 users.FacebookUser )

		assert_that( fb_user, is_( same_instance( user ) ) )
		assert_that( fb_user, provides( nti_interfaces.IFacebookUser ) )
		assert_that( fb_user, has_property( 'facebook_url', 'http://facebook.com' ) )

		# We have fired modified events for the addition of the interface
		# and the change of the URL
		mod_events = eventtesting.getEvents(IObjectModifiedEvent, lambda evt: evt.object == fb_user)
		assert_that( mod_events, has_length( 1 ) )
		assert_that( mod_events[0], has_property( 'object', fb_user ) )
		assert_that( mod_events[0].descriptions, has_item( has_property( 'attributes', has_item( 'facebook_url' ) ) ) )



from zope.lifecycleevent.interfaces import IObjectAddedEvent, IObjectModifiedEvent
_user_added_events = []
@component.adapter(nti_interfaces.IUser,IObjectAddedEvent)
def _handle_user_add_event( user, object_added ):

	_user_added_events.append( (user,object_added) )
