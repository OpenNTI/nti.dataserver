#!/usr/bin/env python2.7
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, not_none, ends_with, starts_with,)
from hamcrest import  has_entry, has_length, has_key,  has_item
from hamcrest import same_instance, greater_than_or_equal_to, greater_than
from hamcrest import contains_string
from hamcrest import contains
from hamcrest import none

from hamcrest.library import has_property
from nti.tests import provides
from nose.tools import assert_raises
import zope.testing.loghandler

import pyramid.testing
#from pyramid.testing import DummyRequest
from nti.tests import ByteHeadersDummyRequest as DummyRequest

from zope import component
from zope import interface
from zope.component import eventtesting

import os

from nti.appserver import logon
from nti.appserver.logon import (ping, handshake,password_logon, google_login, openid_login, ROUTE_OPENID_RESPONSE, _update_users_content_roles)
from nti.appserver.link_providers import flag_link_provider as user_link_provider

from nti.appserver.tests import NewRequestSharedConfiguringTestBase
from .test_application import SharedApplicationTestBase
from .test_application import WithSharedApplicationMockDS
from .test_application import TestApp
from nti.dataserver.tests import mock_dataserver
from pyramid.threadlocal import get_current_request

import pyramid.httpexceptions as hexc
import pyramid.request

from nti.dataserver import authorization as nauth
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans#, WithMockDS

#from nti.tests import provides

import nti.dataserver.interfaces as nti_interfaces
import nti.appserver.interfaces as app_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.externalization.externalization import EXT_FORMAT_JSON, to_external_representation, to_external_object
from nti.dataserver import users
from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary
from nti.contentlibrary import interfaces as lib_interfaces

class DummyView(object):
	response = "Response"
	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		return self.response

class TestApplicationLogon(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_impersonate(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			admin_user = self._create_user( ) # relying on default role
			other_user = self._create_user( 'nobody@nowhere' )
			#admin_user_username = admin_user.username
			other_user_username = other_user.username

		testapp = TestApp( self.app )

		# Forbidden
		testapp.get( '/dataserver2/logon.nti.impersonate', extra_environ=self._make_extra_environ( username=other_user_username ),
					 status=403 )

		# Bad request
		testapp.get( '/dataserver2/logon.nti.impersonate', extra_environ=self._make_extra_environ(  ),
					 status=400 )

		# User that does not exist
		testapp.get( '/dataserver2/logon.nti.impersonate', params={'username': other_user_username + 'dne' },
					 extra_environ=self._make_extra_environ(),
					 status=404)

		# Good request
		res = testapp.get( '/dataserver2/logon.nti.impersonate', params={'username': other_user_username},
						   extra_environ=self._make_extra_environ() )
		assert_that( testapp.cookies, has_key( 'nti.auth_tkt' ) )
		assert_that( testapp.cookies, has_entry( 'username', other_user_username ) )
		assert_that( res.cache_control, has_property( 'max_age', none() ) )
		assert_that( res.cache_control, has_property( 'no_cache', '*' ) )
		# Test that the username cookie comes back correctly 'raw' as well
		cookie_headers = res.headers.dict_of_lists()['set-cookie']
		assert_that( cookie_headers, has_item( 'username=nobody@nowhere; Path=/' ) )


class TestLogonViews(NewRequestSharedConfiguringTestBase):

	def setUp(self):
		super(TestLogonViews,self).setUp()
		eventtesting.clearEvents()
		del _user_created_events[:]
		self.log_handler = zope.testing.loghandler.Handler(self)

	def tearDown(self):
		self.log_handler.close()
		policy = component.queryUtility( pyramid.interfaces.IAuthenticationPolicy )
		if policy:
			component.globalSiteManager.unregisterUtility( policy, provided=pyramid.interfaces.IAuthenticationPolicy )
		super(TestLogonViews,self).tearDown()

	@classmethod
	def setUpClass( self, request_factory=DummyRequest, request_args=() ):
		super(TestLogonViews,self).setUpClass( request_factory=request_factory, request_args=request_args )
		component.provideHandler( _handle_user_create_event )

		self.config.add_route( name='logon.handshake', pattern='/dataserver2/handshake' )
		self.config.add_route( name='logon.nti.password', pattern='/dataserver2/logon.password' )
		self.config.add_route( name='logon.google', pattern='/dataserver2/logon.google' )
		self.config.add_route( name='logon.openid', pattern='/dataserver2/logon.openid' )
		self.config.add_route( name='logon.facebook.oauth1', pattern='/dataserver2/logon.facebook.1' )

		self.config.add_route( name='logon.forgot.username', pattern='/dataserver2/logon.forgot.username' )
		self.config.add_route( name='logon.forgot.passcode', pattern='/dataserver2/logon.forgot.passcode' )
		self.config.add_route( name='logon.reset.passcode', pattern='/dataserver2/logon.reset.passcode' )

		self.config.add_route( name='logon.logout', pattern='/dataserver2/logon.logout' )

		self.config.add_route( name='objects.generic.traversal', pattern='/dataserver2/*traverse' )
		self.config.add_route( name='user.root.service', pattern='/dataserver2{_:/?}' )

		# Provide a library
		library = FileLibrary( os.path.join( os.path.dirname(__file__), 'ExLibrary' ) )
		component.provideUtility( library, lib_interfaces.IContentPackageLibrary )

	def test_unathenticated_ping(self):
		"An unauthenticated ping returns one link, to the handshake."

		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 6 ) ) )
		__traceback_info__ = result.links
		assert_that( result.links[-2].target, ends_with( '/dataserver2/handshake' ) )
		assert_that( result.links[0].target, ends_with( '/dataserver2/users' ) )
		assert_that( result.links[0].elements, is_( ('@@account.create',) ) )
		assert_that( result.links[0].target_mime_type, is_( 'application/vnd.nextthought.user' ) )
		to_external_representation( result, EXT_FORMAT_JSON, name='wsgi' )


	@WithMockDSTrans
	def _test_authenticated_ping(self):
		"An authenticated ping returns two links, to the handshake and the root"

		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'
		user = users.User.create_user( dataserver=self.ds, username='jason.madden@nextthought.com' )
		get_current_request().registry.registerUtility( Policy() )
		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( greater_than_or_equal_to( 3 ) ) ) )
		len_links = len(result.links)
		assert_that( result.links[0].target, ends_with( '/dataserver2/handshake' ) )
		assert_that( result.links[1].target, ends_with( '/dataserver2' ) )

		# We can increase that by adding links
		user_link_provider.add_link( user, 'force-edit-profile' )
		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( len_links + 1 ) ) )
		external = to_external_object( result )
		assert_that( external, has_entry( 'Links', has_length( len_links + 1 ) ) )
		assert_that( external['Links'][3], has_entry( 'href', '/dataserver2/users/jason.madden%40nextthought.com/@@force-edit-profile' ) )

		# and we can decrease again
		user_link_provider.delete_link( user, 'force-edit-profile' )
		result = ping( get_current_request() )
		assert_that( result, has_property( 'links', has_length( len_links ) ) )

	@WithMockDSTrans
	def test_fake_authenticated_handshake(self):

		# A user that doesn't actually exist.
		# Per current policy, the first link will be the generic password login
		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'

		component.provideUtility( Policy() )
		get_current_request().params['username'] = 'jason.madden@nextthought.com'

		result = handshake( get_current_request() )
		assert_that( result, has_property( 'links', has_length( greater_than_or_equal_to( 3 ) ) ) )
		__traceback_info__ = result.links
		assert_that( result.links[5].target, contains_string( '/dataserver2/logon.google?') )
		assert_that( result.links[5].target, contains_string( 'username=jason.madden%40nextthought.com' ) )
		assert_that( result.links[5].target, contains_string( 'oidcsum=1290829754' ) )

		assert_that( result.links[2].target, is_( '/dataserver2/logon.facebook.1?username=jason.madden%40nextthought.com' ) )
		#assert_that( result.links[3].target, is_( '/dataserver2' ) )
		#assert_that( result.links[4].target, is_( '/dataserver2/logon.logout' ) )

	def test_handshake_no_user(self):
		assert_that( handshake( get_current_request() ), is_( hexc.HTTPBadRequest ) )

	@WithMockDSTrans
	def test_handshake_existing_user_with_pass(self):
		# Clean up routes we don't yet want
		for route_name in ('logon.google', 'logon.openid', 'logon.facebook.oauth1', 'logon.forgot.passcode', 'logon.forgot.username' ):
			route = component.getUtility( pyramid.interfaces.IRouteRequest, name=route_name )
			__traceback_info__ = route_name, route
			assert component.globalSiteManager.unregisterUtility( route, provided=pyramid.interfaces.IRouteRequest, name=route_name )

		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com', password='temp001' )

		get_current_request().params['username'] = 'jason.madden@nextthought.com'

		# Give us the capability to do a google logon, and we can
		self.config.add_route( name='logon.google', pattern='/dataserver2/logon.google' )
		result = handshake( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 7 ) ) )
		__traceback_info__ = result.links
		assert_that( result.links[-2].target, contains_string( '/dataserver2/logon.password?' ) )
		assert_that( result.links[-3].target, contains_string( '/dataserver2/logon.google?') )
		assert_that( result.links[-3].target, contains_string( 'username=jason.madden%40nextthought.com' ) )
		assert_that( result.links[-3].target, contains_string( 'oidcsum=1290829754' ) )


		# Give us a specific identity_url, and that changes to open id
		self.config.add_route( name='logon.openid', pattern='/dataserver2/logon.openid' )
		user.identity_url = 'http://google.com/foo'
		interface.alsoProvides( user, nti_interfaces.IOpenIdUser )
		result = handshake( get_current_request() )
		assert_that( result, has_property( 'links', has_length( 7 ) ) )
		__traceback_info__ = result.links
		assert_that( result.links[-3].target, is_( '/dataserver2/logon.password?username=jason.madden%40nextthought.com' ) )
		assert_that( result.links[-2].target, contains_string( '/dataserver2/logon.openid?') )
		assert_that( result.links[-2].target, contains_string( 'username=jason.madden%40nextthought.com' ) )
		assert_that( result.links[-2].target, contains_string( 'oidcsum=1290829754' ) )
		assert_that( result.links[-2].target, contains_string( 'openid=http' ) )

	def test_openid_login( self ):
		fail = google_login( None, get_current_request() )
		assert_that( fail, is_( hexc.HTTPUnauthorized ) )
		fail = openid_login( None, get_current_request() )
		assert_that( fail, is_( hexc.HTTPUnauthorized ) )

		from pyramid.session import UnencryptedCookieSessionFactoryConfig
		my_session_factory = UnencryptedCookieSessionFactoryConfig('ntidataservercookiesecretpass')
		self.config.set_session_factory( my_session_factory )
		self.config.add_route( name=ROUTE_OPENID_RESPONSE, pattern='/dataserver2/' + ROUTE_OPENID_RESPONSE )

		# TODO: This test is assuming we have access to google.com
		get_current_request().params['oidcsum'] = '1234'
		self.log_handler.add( 'pyramid_openid.view' )
		result = google_login( None, get_current_request() )
		assert_that( result, is_( hexc.HTTPFound ) )
		assert_that( result.location, starts_with( 'https://www.google.com/accounts/o8/' ) )
		redir_url = None
		for r in self.log_handler.records:
			if (r.getMessage() or '' ).startswith( 'Redirecting to: ' ):
				redir_url = r.getMessage()[len('Redirecting to: '):]
				break
		assert_that( redir_url, is_( not_none() ) )
		# TODO: These prefixes are probably order dependent and fragile
		assert_that( redir_url, contains_string( '=unlimited' ) )
		assert_that( redir_url, contains_string( 'ax.if_available=ext' ) )

		# An openid request to a non-existant domain will fail
		# to begin negotiation
		get_current_request().params['openid'] = 'http://localhost/oidprovider/'
		result = openid_login( None, get_current_request() )
		assert_that( result, is_( hexc.HTTPUnauthorized ) )
		assert_that( result.headers, has_key( 'Warning' ) )


	def test_password_logon_failed(self):
		self.beginRequest(request_factory=pyramid.request.Request.blank, request_args=('/',))
		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def forget( self, request ):
				return [("Policy", "Me")]
			def authenticated_userid( self, request ): return None
		component.provideUtility( Policy() )
		#get_current_request().registry.registerUtility( Policy() )
		result = password_logon( get_current_request() )
		assert_that( result, is_( hexc.HTTPUnauthorized ) )
		assert_that( result.headers, has_entry( "Policy", "Me" ) )

        # Or a redirect
		self.beginRequest(request_factory=pyramid.request.Request.blank, request_args=('/?failure=/the/url/to/go/to',))
		#get_current_request().registry.registerUtility( Policy() )
		#get_current_request().params['failure'] = '/the/url/to/go/to'
		result = password_logon( get_current_request() )
		assert_that( result, is_( hexc.HTTPSeeOther ) )
		assert_that( result.headers, has_entry( "Policy", "Me" ) )
		assert_that( result, has_property( 'location', '/the/url/to/go/to' ) )

	@WithMockDSTrans
	def test_password_logon_success(self):
		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com', password='temp001' )

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
		# The event fired
		assert_that( user.lastLoginTime,
					 is_( greater_than( 0 ) ) )

        # Or a redirect
		get_current_request().params['success'] = '/the/url/to/go/to'
		result = password_logon( get_current_request() )
		assert_that( result, is_( hexc.HTTPSeeOther ) )
		assert_that( result.headers, has_entry( "Policy", 'jason.madden@nextthought.com') )
		assert_that( result, has_property( 'location', '/the/url/to/go/to' ) )

	@WithMockDSTrans
	def test_create_openid_from_external( self ):
		user = logon._deal_with_external_account( get_current_request(),
												  "jason.madden@nextthought.com",
												  "Jason",
												  "Madden",
												  "jason.madden@nextthought.com",
												  "http://example.com",
												  nti_interfaces.IOpenIdUser,
												  users.OpenIdUser.create_user )
		assert_that( user, provides( nti_interfaces.IOpenIdUser ) )
		assert_that( user, is_( users.OpenIdUser ) )
		assert_that( user, has_property( 'identity_url', 'http://example.com' ) )
		assert_that( user_interfaces.IUserProfile( user ), has_property( 'realname', 'Jason Madden' ) )
		assert_that( user_interfaces.IUserProfile( user ), has_property( 'email', 'jason.madden@nextthought.com' ) )

		# The creation of this user caused events to fire
		assert_that( eventtesting.getEvents(), has_length( greater_than_or_equal_to( 1 ) ) )

		assert_that( _user_created_events, has_length( 1 ) )
		assert_that( _user_created_events[0][0], is_( same_instance( user ) ) )
		# We created a new user during a request, so that event fired
		assert_that( eventtesting.getEvents(app_interfaces.IUserCreatedWithRequestEvent), has_length( 1 ) )

		# Can also auth as facebook for the same email address
		# TODO: Think about that
		fb_user = logon._deal_with_external_account( get_current_request(),
													 "jason.madden@nextthought.com",
													 "Jason",
													 "Madden",
													 "jason.madden@nextthought.com",
													 "http://facebook.com",
													 nti_interfaces.IFacebookUser,
													 users.FacebookUser.create_user )

		assert_that( fb_user, is_( same_instance( user ) ) )
		assert_that( fb_user, provides( nti_interfaces.IFacebookUser ) )
		assert_that( fb_user, has_property( 'facebook_url', 'http://facebook.com' ) )

		# We have fired modified events for the addition of the interface
		# and the change of the URL
		mod_events = eventtesting.getEvents(IObjectModifiedEvent, lambda evt: evt.object == fb_user)
		assert_that( mod_events, has_length( 1 ) )
		assert_that( mod_events[0], has_property( 'object', fb_user ) )
		assert_that( mod_events[0].descriptions, has_item( has_property( 'attributes', has_item( 'facebook_url' ) ) ) )

		# But the created-with-request did not fire
		assert_that( eventtesting.getEvents(app_interfaces.IUserCreatedWithRequestEvent), has_length( 1 ) )

	@WithMockDSTrans
	def test_create_facebook_from_external( self ):

		fb_user = logon._deal_with_external_account( get_current_request(),
													 "jason.madden@nextthought.com",
													 "Jason",
													 "Madden",
													 "jason.madden@nextthought.com",
													 "http://facebook.com",
													 nti_interfaces.IFacebookUser,
													 users.FacebookUser.create_user )


		assert_that( fb_user, provides( nti_interfaces.IFacebookUser ) )
		assert_that( fb_user, has_property( 'facebook_url', 'http://facebook.com' ) )

		# The creation of this user caused events to fire
		assert_that( eventtesting.getEvents(), has_length( greater_than_or_equal_to( 1 ) ) )

		assert_that( _user_created_events, has_length( 1 ) )
		assert_that( _user_created_events[0][0], is_( same_instance( fb_user ) ) )
		# We created a new user during a request, so that event fired
		assert_that( eventtesting.getEvents(app_interfaces.IUserCreatedWithRequestEvent), has_length( 1 ) )


	@WithMockDSTrans
	def test_create_from_external_bad_data( self ):
		with assert_raises(hexc.HTTPError):
			logon._deal_with_external_account( get_current_request(),
											   "jason.madden@nextthought.com",
											   "Jason",
											   "Madden",
											   "jason.madden_nextthought_com", # Bad email
											   "http://facebook.com",
											   nti_interfaces.IFacebookUser,
											   users.FacebookUser.create_user )
	@WithMockDSTrans
	def test_update_provider_content_access_not_in_library(self):
		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com', password='temp001' )
		content_roles = component.getAdapter( user, nti_interfaces.IGroupMember, nauth.CONTENT_ROLE_PREFIX )
		# initially empty
		assert_that( list(content_roles.groups), is_( [] ) )

		# add some from this provider
		idurl = 'http://openid.nextthought.com/jmadden'
		local_roles = ('ABCD',)
		_update_users_content_roles( user, idurl, local_roles )
		assert_that( content_roles.groups, contains( *[nauth.role_for_providers_content( 'nextthought', x ) for x in local_roles] ) )


		# add some more from this provider
		local_roles += ('DEFG',)
		_update_users_content_roles( user, idurl, local_roles )

		assert_that( content_roles.groups, contains( *[nauth.role_for_providers_content( 'nextthought', x ) for x in local_roles] ) )

		# Suppose that this user has some other roles too from a different provider
		aops_roles = [nauth.role_for_providers_content( 'aops', '1234')]
		complete_roles = aops_roles + [nauth.role_for_providers_content( 'nextthought', x ) for x in local_roles]
		assert_that( complete_roles, has_length( 3 ) )
		content_roles.setGroups( complete_roles )

		# If we update NTI again...
		_update_users_content_roles( user, idurl, local_roles )
		# nothing changes.
		assert_that( content_roles.groups, contains( *complete_roles ) )

		# We can change up the NTI roles...
		local_roles = ('HIJK',)
		_update_users_content_roles( user, idurl, local_roles )
		complete_roles = aops_roles + [nauth.role_for_providers_content( 'nextthought', x ) for x in local_roles]
		# and the aops roles are intact
		assert_that( complete_roles, has_length( 2 ) )
		assert_that( content_roles.groups, contains( *complete_roles ) )

		# We can remove the NTI roles
		_update_users_content_roles( user, idurl, None )
		# leaving the other roles behind
		assert_that( content_roles.groups, contains( *aops_roles ) )


	@WithMockDSTrans
	def test_update_provider_content_access_in_library(self):
		"""If we supply the title of a work, the works actual NTIID gets used."""
		# There are two things with the same title in the library, but different ntiids
		# label="COSMETOLOGY" ntiid="tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.cosmetology"
		# label="COSMETOLOGY" ntiid="tag:nextthought.com,2011-10:MN-HTML-uncensored.cosmetology"

		user = users.User.create_user( self.ds, username='jason.madden@nextthought.com', password='temp001' )
		content_roles = component.getAdapter( user, nti_interfaces.IGroupMember, nauth.CONTENT_ROLE_PREFIX )
		# initially empty
		assert_that( list(content_roles.groups), is_( [] ) )

		# Provider of course has to match
		idurl = 'http://openid.mn.com/jmadden'
		# The role is the title of the work
		local_roles = ('cosmetology',)

		_update_users_content_roles( user, idurl, local_roles )

		assert_that( content_roles.groups, contains( nauth.role_for_providers_content( 'mn', 'MiladyCosmetology.cosmetology' ),
													 nauth.role_for_providers_content( 'mn', 'Uncensored.cosmetology' ) ) )


from zope.lifecycleevent.interfaces import IObjectCreatedEvent, IObjectModifiedEvent
_user_created_events = []
@component.adapter(nti_interfaces.IUser,IObjectCreatedEvent)
def _handle_user_create_event( user, object_added ):

	_user_created_events.append( (user,object_added) )
