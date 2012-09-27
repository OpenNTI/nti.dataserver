#!/usr/bin/env python2.7
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, not_none, ends_with, starts_with,)
from hamcrest import  has_entry, has_length, has_key,  has_item
from hamcrest import same_instance, greater_than_or_equal_to, greater_than

from hamcrest.library import has_property
from nti.tests import provides
from zope import component
from zope.component import eventtesting, provideHandler

from nti.appserver import logon
from nti.appserver.logon import (ping, handshake,password_logon, google_login, openid_login)
from nti.appserver import user_link_provider

from nti.appserver.tests import ConfiguringTestBase
from pyramid.threadlocal import get_current_request

import pyramid.testing
import pyramid.httpexceptions as hexc



from nti.dataserver.tests.mock_dataserver import WithMockDSTrans, WithMockDS
#from nti.tests import provides

from zope import interface
import nti.dataserver.interfaces as nti_interfaces

from nti.externalization.externalization import EXT_FORMAT_JSON, to_external_representation, to_external_object
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
		del _user_created_events[:]

	def test_unathenticated_ping(self):
		"An unauthenticated ping returns one link, to the handshake."
		self.config.add_route( name='logon.handshake', pattern='/dataserver2/handshake' )
		self.config.add_route( name='objects.generic.traversal', pattern='/dataserver2/*traverse' )
		self.config.add_route( name='logon.forgot.username', pattern='/dataserver2/logon.forgot.username' )
		self.config.add_route( name='logon.forgot.passcode', pattern='/dataserver2/logon.forgot.passcode' )
		self.config.add_route( name='logon.reset.passcode', pattern='/dataserver2/logon.reset.passcode' )

		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 6 ) ) )
		assert_that( result.links[0].target, ends_with( '/dataserver2/handshake' ) )
		assert_that( result.links[1].target, ends_with( '/dataserver2/users' ) )
		assert_that( result.links[1].elements, is_( ('@@account.create',) ) )
		assert_that( result.links[1].target_mime_type, is_( 'application/vnd.nextthought.user' ) )
		to_external_representation( result, EXT_FORMAT_JSON, name='wsgi' )


	@WithMockDSTrans
	def test_authenticated_ping(self):
		"An authenticated ping returns two links, to the handshake and the root"
		self.config.add_route( name='user.root.service', pattern='/dataserver2{_:/?}' )
		self.config.add_route( name='logon.handshake', pattern='/dataserver2/handshake' )
		self.config.add_route( name='logon.logout', pattern='/dataserver2/logon.logout' )
		self.config.add_route( name='objects.generic.traversal', pattern='/dataserver2/*traverse' )
		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'
		user = users.User.create_user( dataserver=self.ds, username='jason.madden@nextthought.com' )
		get_current_request().registry.registerUtility( Policy() )
		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 3 ) ) )
		assert_that( result.links[0].target, ends_with( '/dataserver2/handshake' ) )
		assert_that( result.links[1].target, ends_with( '/dataserver2' ) )

		# We can increase that by adding links
		user_link_provider.add_link( user, 'force-edit-profile' )
		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 4 ) ) )
		external = to_external_object( result )
		assert_that( external, has_entry( 'Links', has_length( 4 ) ) )
		assert_that( external['Links'][3], has_entry( 'href', '/dataserver2/users/jason.madden%40nextthought.com/@@force-edit-profile' ) )

		# and we can decrease again
		user_link_provider.delete_link( user, 'force-edit-profile' )
		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 3 ) ) )

	@WithMockDSTrans
	def test_fake_authenticated_handshake(self):

		self.config.add_route( name='user.root.service', pattern='/dataserver2{_:/?}' )
		self.config.add_route( name='objects.generic.traversal', pattern='/dataserver2/*traverse' )
		self.config.add_route( name='logon.handshake', pattern='/dataserver2/handshake' )
		self.config.add_route( name='logon.nti.password', pattern='/dataserver2/logon.password' )
		self.config.add_route( name='logon.google', pattern='/dataserver2/logon.google' )
		self.config.add_route( name='logon.logout', pattern='/dataserver2/logon.logout' )
		self.config.add_route( name='logon.facebook.oauth1', pattern='/dataserver2/logon.facebook.1' )

		# A user that doesn't actually exist.
		# Per current policy, the first link will be the generic password login
		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'

		get_current_request().registry.registerUtility( Policy() )
		get_current_request().params['username'] = 'jason.madden@nextthought.com'

		result = handshake( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 3 ) ) )
		assert_that( result.links[1].target, is_( '/dataserver2/logon.google?username=jason.madden%40nextthought.com&oidcsum=-1978826904171095151' ) )
		assert_that( result.links[2].target, is_( '/dataserver2/logon.facebook.1?username=jason.madden%40nextthought.com' ) )
		#assert_that( result.links[3].target, is_( '/dataserver2' ) )
		#assert_that( result.links[4].target, is_( '/dataserver2/logon.logout' ) )

	def test_handshake_no_user(self):
		assert_that( handshake( get_current_request() ), is_( hexc.HTTPBadRequest ) )

	@WithMockDSTrans
	def test_handshake_existing_user_with_pass(self):
		self.config.add_route( name='logon.nti.password', pattern='/dataserver2/logon.nti.password' )
		self.config.add_route( name='logon.forgot.username', pattern='/dataserver2/logon.forgot.username' )
		self.config.add_route( name='logon.forgot.passcode', pattern='/dataserver2/logon.forgot.passcode' )
		self.config.add_route( name='logon.reset.passcode', pattern='/dataserver2/logon.reset.passcode' )
		self.config.add_route( name='objects.generic.traversal', pattern='/dataserver2/*traverse' )
		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com', password='temp001' )

		get_current_request().params['username'] = 'jason.madden@nextthought.com'

		# With no other routes present, and us having a password, we can
		# login that way
		result = handshake( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 6 ) ) )
		assert_that( result.links[0].target, is_( '/dataserver2/logon.nti.password?username=jason.madden%40nextthought.com' ) )


		# Give us the capability to do a google logon, and we can
		self.config.add_route( name='logon.google', pattern='/dataserver2/logon.google' )
		result = handshake( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 7 ) ) )
		assert_that( result.links[0].target, is_( '/dataserver2/logon.nti.password?username=jason.madden%40nextthought.com' ) )
		assert_that( result.links[1].target, is_( '/dataserver2/logon.google?username=jason.madden%40nextthought.com&oidcsum=-1978826904171095151' ) )

		# Give us a specific identity_url, and that changes to open id
		self.config.add_route( name='logon.openid', pattern='/dataserver2/logon.openid' )
		user.identity_url = 'http://google.com/foo'
		interface.alsoProvides( user, nti_interfaces.IOpenIdUser )
		result = handshake( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 7 ) ) )
		assert_that( result.links[0].target, is_( '/dataserver2/logon.nti.password?username=jason.madden%40nextthought.com' ) )
		assert_that( result.links[1].target, is_( '/dataserver2/logon.openid?username=jason.madden%40nextthought.com&openid=http%3A%2F%2Fgoogle.com%2Ffoo&oidcsum=-1978826904171095151' ) )

	def test_openid_login( self ):
		fail = google_login( None, get_current_request() )
		assert_that( fail, is_( hexc.HTTPUnauthorized ) )
		fail = openid_login( None, get_current_request() )
		assert_that( fail, is_( hexc.HTTPUnauthorized ) )

		from pyramid.session import UnencryptedCookieSessionFactoryConfig
		my_session_factory = UnencryptedCookieSessionFactoryConfig('ntidataservercookiesecretpass')
		self.config.set_session_factory( my_session_factory )
		self.config.add_route( name='logon.google.result', pattern='/dataserver2/logon.google.result' )

		# TODO: This test is assuming we have access to google.com
		get_current_request().params['oidcsum'] = '1234'
		result = google_login( None, get_current_request() )
		assert_that( result, is_( hexc.HTTPFound ) )
		assert_that( result.location, starts_with( 'https://www.google.com/accounts/o8/' ) )

		# An openid request to a non-existant domain will fail
		# to begin negotiation
		get_current_request().params['openid'] = 'http://localhost/oidprovider/'
		result = openid_login( None, get_current_request() )
		assert_that( result, is_( hexc.HTTPUnauthorized ) )
		assert_that( result.headers, has_key( 'Warning' ) )


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

	@WithMockDSTrans
	def test_password_logon_success(self):
		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def remember( self, request, who ):
				return [("Policy", who)]
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'
		get_current_request().registry.registerUtility( Policy() )
		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com', password='temp001' )
		user.lastLoginTime.value = 0
		result = password_logon( get_current_request() )
		assert_that( result, is_( hexc.HTTPNoContent ) )
		assert_that( result.headers, has_entry( "Policy", 'jason.madden@nextthought.com' ) )
		# The event fired
		assert_that( user.lastLoginTime,
					 has_property( 'value', greater_than( 0 ) ) )

        # Or a redirect
		get_current_request().params['success'] = '/the/url/to/go/to'
		result = password_logon( get_current_request() )
		assert_that( result, is_( hexc.HTTPSeeOther ) )
		assert_that( result.headers, has_entry( "Policy", 'jason.madden@nextthought.com') )
		assert_that( result, has_property( 'location', '/the/url/to/go/to' ) )

	@WithMockDSTrans
	def test_create_from_external( self ):
		component.provideHandler( eventtesting.events.append, (None,) )
		component.provideHandler( _handle_user_create_event )

		# For now, we are adding to some predefined communities
		mc = users.Community( 'MathCounts' )
		self.ds.root['users'][mc.username] = mc
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

		# This:
		#assert_that( users.Entity.get_entity( 'MathCounts' ), not_none() )
		#assert_that( user.communities, has_item( 'MathCounts' ) )
		#assert_that( user.following, has_item( 'MathCounts' ) )
		# Only happens if this:
		#self.request.headers['origin'] = 'http://mathcounts.nextthought.com'
		# happened first. But as the policies are getting stricter, that's not
		# possible.

		# The creation of this user caused events to fire
		assert_that( eventtesting.getEvents(), has_length( greater_than_or_equal_to( 1 ) ) )
		assert_that( _user_created_events, has_length( 1 ) )
		assert_that( _user_created_events[0][0], is_( same_instance( user ) ) )

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



from zope.lifecycleevent.interfaces import IObjectCreatedEvent, IObjectModifiedEvent
_user_created_events = []
@component.adapter(nti_interfaces.IUser,IObjectCreatedEvent)
def _handle_user_create_event( user, object_added ):

	_user_created_events.append( (user,object_added) )
