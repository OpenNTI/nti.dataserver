#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge

from hamcrest import is_
from hamcrest import not_
from hamcrest import all_of
from hamcrest import has_key
from hamcrest import equal_to
from hamcrest import has_item
from hamcrest import ends_with
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than
from hamcrest import has_property
from hamcrest import same_instance
from hamcrest import starts_with
from hamcrest import contains_string
from hamcrest import greater_than_or_equal_to

from nose.tools import assert_raises

from nti.testing.matchers import is_true
from nti.testing.matchers import provides
from nti.testing.matchers import verifiably_provides

import zope.testing.loghandler

from six.moves.urllib_parse import quote

from zope import component
from zope import interface

from zope.component import eventtesting

from zope.component.hooks import setSite
from zope.component.hooks import clearSite

import pyramid.interfaces
import pyramid.request
import pyramid.httpexceptions as hexc

from pyramid.session import JSONSerializer

from pyramid.threadlocal import get_current_request

from nti.appserver import interfaces as app_interfaces

from nti.appserver import logon

from nti.appserver.interfaces import IAuthenticatedUserLinkProvider

from nti.appserver.logon import REL_INVALID_EMAIL
from nti.appserver.logon import REL_INVALID_CONTACT_EMAIL
from nti.appserver.logon import REL_INITIAL_WELCOME_PAGE
from nti.appserver.logon import REL_INITIAL_TOS_PAGE
from nti.appserver.logon import ROUTE_OPENID_RESPONSE

from nti.appserver.logon import ping
from nti.appserver.logon import handshake
from nti.appserver.logon import _checksum
from nti.appserver.logon import openid_login
from nti.appserver.logon import password_logon
from nti.appserver.logon import _openidcallback
from nti.appserver.logon import DoNotAdvertiseWelcomePageLinksProvider

from nti.appserver.link_providers import flag_link_provider as user_link_provider

from nti.dataserver import users

from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.users import interfaces as user_interfaces

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.externalization.externalization import EXT_FORMAT_JSON
from nti.externalization.externalization import to_external_object
from nti.externalization.representation import to_external_representation

from nti.site.site import get_site_for_site_names

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.application_webtest import ApplicationTestLayer

from nti.appserver.tests.test_application import TestApp
from nti.appserver.tests.test_application import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import User


class DummyView(object):
	response = "Response"

	def __init__(self, request):
		self.request = request

	def __call__(self):
		return self.response

class TestApplicationLogon(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_mallowstreet_account_creation(self):
		testapp = TestApp(self.app, extra_environ={b'HTTP_ORIGIN': b'http://prmia.nextthought.com'})

		username = 'thomas.stockdale@example.com@mallowstreet.com'
		res = testapp.post('/dataserver2/logon.handshake', params={'username': username})
		assert_that(res.cache_control, has_property('private', '*'))
		assert_that(res.cache_control, has_property('no_store', is_true()))
		assert_that(res.cache_control, has_property('no_cache', '*'))
		self.require_link_href_with_rel(res.json_body, 'logon.openid')
		oid_link = self.link_with_rel(res.json_body, 'logon.openid')
		assert_that(oid_link, has_entry('title', 'Sign in with mallowstreet.com'))

		# TODO: This would actually try to contact the remote server to do
		# discovery. Need to mock that
		# testapp.get( oid_link, status=302 )

		# Now test the callback
		csum = _checksum(username)
		with mock_dataserver.mock_db_trans(self.ds):
			setSite(get_site_for_site_names(('prmia.nextthought.com',)))
			try:
				self.request.params['oidcsum'] = csum
				success_dict = { 'identity_url': 'https://demo.mallowstreet.com/thomas.stockdale@example.com',
								 'ax': { 'firstname': ['Tom'],
										 'lastname': ['Stockdale'],
										 'email': ['tom@nextthought.com']}}
				try:
					_openidcallback(None, self.request, success_dict)
					raise ValueError("Expected attribute error dealing with logon cookies")
				except AttributeError:
					pass

			finally:
				clearSite()

		with mock_dataserver.mock_db_trans(self.ds):
			# Which created the user, yay!
			assert_that(users.User.get_user(username), verifiably_provides(nti_interfaces.IOpenIdUser))

	@WithSharedApplicationMockDS
	def test_impersonate(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()  # relying on default role / admin user
			other_user = self._create_user('nobody@nowhere')
			other_user_username = other_user.username
			nt_user = self._create_user('chris@nextthought.com')
			nt_user_username = nt_user.username

		testapp = TestApp(self.app)
		nobody_env = self._make_extra_environ(username=other_user_username)
		# Forbidden
		testapp.get('/dataserver2/logon.nti.impersonate',
					 extra_environ=nobody_env,
					 status=403)
		# He doesn't get a link for it on a ping or handshake anyway
		res = testapp.get('/dataserver2/logon.ping',
						  extra_environ=nobody_env)
		self.forbid_link_with_rel(res.json_body, 'logon.nti.impersonate')
		res = testapp.post('/dataserver2/logon.handshake',
						   params={'username': other_user_username})
		self.forbid_link_with_rel(res.json_body, 'logon.nti.impersonate')

		# Bad request
		testapp.get('/dataserver2/logon.nti.impersonate', extra_environ=self._make_extra_environ(),
					 status=400)

		# User that does not exist
		testapp.get('/dataserver2/logon.nti.impersonate', params={'username': other_user_username + 'dne' },
					 extra_environ=self._make_extra_environ(),
					 status=404)

		# @nextthought.com accounts can't be impersonated, even by other @nextthought.com accounts
		testapp.get('/dataserver2/logon.nti.impersonate', params={'username': nt_user_username },
					 extra_environ=self._make_extra_environ(),
					 status=403)

		# Good request...
		# right person gets it in ping
		res = testapp.get('/dataserver2/logon.ping',
						  extra_environ=self._make_extra_environ())
		self.require_link_href_with_rel(res.json_body, 'logon.nti.impersonate')

		res = testapp.get('/dataserver2/logon.nti.impersonate',
						   params={'username': other_user_username},
						   extra_environ=self._make_extra_environ())
		assert_that(testapp.cookies, has_key('nti.auth_tkt'))
		# The auth_tkt cookie contains both the original and new username
		quoted = quote(self.extra_environ_default_user.lower())
		assert_that(testapp.cookies['nti.auth_tkt'], all_of(contains_string('nobody%40nowhere'),
															  contains_string(quoted)))
		assert_that(testapp.cookies, has_entry('username', other_user_username))
		assert_that(res.cache_control, has_property('max_age', 0))
		assert_that(res.cache_control, has_property('no_cache', '*'))
		assert_that(res.cache_control, has_property('private', '*'))
		assert_that(res.cache_control, has_property('no_store', is_true()))

		# Test that the username cookie comes back correctly 'raw' as well
		cookie_headers = res.headers.dict_of_lists()['set-cookie']
		assert_that(cookie_headers, has_item('username=nobody@nowhere; Path=/'))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=False)
	def test_password_logon(self):
		testapp = self.testapp
		res = testapp.get('/dataserver2/logon.nti.password',
						   extra_environ=self._make_extra_environ())
		assert_that(res.headers.dict_of_lists()['set-cookie'],
					 has_length(4))  # username, 3 variations on auth_tkt for domains
		assert_that(testapp.cookies, has_key('nti.auth_tkt'))
		# The auth_tkt cookie contains both the original and new username
		assert_that(testapp.cookies['nti.auth_tkt'],
					 contains_string('sjohnson%40nextthought.com!'))

		# The auth_tkt cookied should not contain any empty username param.
		# e.g. "username="  The username param is currently being used to signify
		# we have impesonated someone
		assert_that(testapp.cookies['nti.auth_tkt'],
					 not_(contains_string('username="')))

		# Now that we have the cookie, we should be able to request ourself
		testapp.get('/dataserver2/users/sjohnson@nextthought.com')


class TestLinkProviders(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=(u'test001',), testapp=True, default_authenticate=False)
	def test_do_not_advertise_welcome_page_link_provider(self):
		from z3c.baseregistry.baseregistry import BaseComponents
		from nti.appserver.policies.sites import BASEADULT
		site = BaseComponents(BASEADULT, name='nonwelcomepagetest.nextthought.com', bases=(BASEADULT,))
		component.provideUtility(site, interface.interfaces.IComponents, name='nonwelcomepagetest.nextthought.com')

		url = '/dataserver2/users/test001'

		extra_environ = self._make_extra_environ(username=u'test001')
		extra_environ.update({b'HTTP_ORIGIN': b'http://nonwelcomepagetest.nextthought.com'})

		# It should show these links by default.
		# We no longer provide these links
		result = self.testapp.get(url, extra_environ=extra_environ)
		result = result.json_body
		self.forbid_link_with_rel(result, 'content.initial_welcome_page')
		self.forbid_link_with_rel(result, 'content.permanent_welcome_page')

		# register DoNotAdvertiseWelcomePageLinksProvider
		site.registerSubscriptionAdapter(DoNotAdvertiseWelcomePageLinksProvider,
										 (nti_interfaces.IUser, pyramid.interfaces.IRequest),
										 IAuthenticatedUserLinkProvider)

		result = self.testapp.get(url, extra_environ=extra_environ)
		result = result.json_body
		self.forbid_link_with_rel(result, 'content.initial_welcome_page')
		self.forbid_link_with_rel(result, 'content.permanent_welcome_page')

		# unregister
		site.unregisterSubscriptionAdapter(DoNotAdvertiseWelcomePageLinksProvider,
										   (nti_interfaces.IUser, pyramid.interfaces.IRequest),
										   IAuthenticatedUserLinkProvider)

		result = self.testapp.get(url, extra_environ=extra_environ)
		result = result.json_body
		self.require_link_href_with_rel(result, 'content.initial_welcome_page')
		self.require_link_href_with_rel(result, 'content.permanent_welcome_page')


	@WithSharedApplicationMockDS(users=(u'test001', u'test002@nextthought.com'), testapp=True, default_authenticate=False)
	@fudge.patch('nti.appserver.decorators.is_impersonating')
	def test_bypassing_links(self, mock_is_impersonating):
		from z3c.baseregistry.baseregistry import BaseComponents
		from nti.appserver.policies.sites import BASEADULT
		site = BaseComponents(BASEADULT, name='nonwelcomepagetest.nextthought.com', bases=(BASEADULT,))
		component.provideUtility(site, interface.interfaces.IComponents, name='testbypassing.nextthought.com')

		with mock_dataserver.mock_db_trans( self.ds ):
			for username in (u'test001', 'test002@nextthought.com'):
				user = User.get_user(username)
				user_link_provider.add_link( user, REL_INVALID_CONTACT_EMAIL )
				user_link_provider.add_link( user, REL_INVALID_EMAIL )

		# normal user, bypassing when it's impersonating.
		username = u'test001'
		url = '/dataserver2/users/%s' % username
		extra_environ = self._make_extra_environ(username=username)
		extra_environ.update({b'HTTP_ORIGIN': b'http://testbypassing.nextthought.com'})

		mock_is_impersonating.is_callable().returns(False)
		result = self.testapp.get(url, extra_environ=extra_environ).json_body
		self.require_link_href_with_rel(result, REL_INITIAL_TOS_PAGE)
		self.forbid_link_with_rel(result, REL_INITIAL_WELCOME_PAGE)
		self.require_link_href_with_rel(result, REL_INVALID_CONTACT_EMAIL)
		self.require_link_href_with_rel(result, REL_INVALID_EMAIL)

		mock_is_impersonating.is_callable().returns(True)
		result = self.testapp.get(url, extra_environ=extra_environ).json_body
		self.forbid_link_with_rel(result, REL_INITIAL_TOS_PAGE)
		self.forbid_link_with_rel(result, REL_INITIAL_WELCOME_PAGE)
		self.forbid_link_with_rel(result, REL_INVALID_CONTACT_EMAIL)
		self.forbid_link_with_rel(result, REL_INVALID_EMAIL)

		# NextThought user, bypassing all
		username = u'test002@nextthought.com'
		url = '/dataserver2/users/%s' % username
		extra_environ = self._make_extra_environ(username=username)
		extra_environ.update({b'HTTP_ORIGIN': b'http://testbypassing.nextthought.com'})

		mock_is_impersonating.is_callable().returns(False)
		result = self.testapp.get(url, extra_environ=extra_environ).json_body
		self.forbid_link_with_rel(result, REL_INITIAL_TOS_PAGE)
		self.forbid_link_with_rel(result, REL_INITIAL_WELCOME_PAGE)
		self.forbid_link_with_rel(result, REL_INVALID_CONTACT_EMAIL)
		self.forbid_link_with_rel(result, REL_INVALID_EMAIL)

		mock_is_impersonating.is_callable().returns(True)
		result = self.testapp.get(url, extra_environ=extra_environ).json_body
		self.forbid_link_with_rel(result, REL_INITIAL_TOS_PAGE)
		self.forbid_link_with_rel(result, REL_INITIAL_WELCOME_PAGE)
		self.forbid_link_with_rel(result, REL_INVALID_CONTACT_EMAIL)
		self.forbid_link_with_rel(result, REL_INVALID_EMAIL)


class LogonViewsLayer(ApplicationTestLayer):
	pass


class TestLogonViews(ApplicationLayerTest):
	layer = LogonViewsLayer # we use our own layer here b/c our tests manipulate the route registry

	def setUp(self):
		super(TestLogonViews, self).setUp()
		eventtesting.clearEvents()
		del _user_created_events[:]
		component.getGlobalSiteManager().registerHandler(_handle_user_create_event)
		self.log_handler = zope.testing.loghandler.Handler(self)
		self.__policy = component.getGlobalSiteManager().queryUtility(pyramid.interfaces.IAuthenticationPolicy)

	def tearDown(self):
		self.log_handler.close()
		policy = component.queryUtility(pyramid.interfaces.IAuthenticationPolicy)
		if policy:
			component.globalSiteManager.unregisterUtility(policy, provided=pyramid.interfaces.IAuthenticationPolicy)
		if self.__policy:
			component.getGlobalSiteManager().registerUtility(self.__policy)
		component.getGlobalSiteManager().unregisterHandler(_handle_user_create_event)
		super(TestLogonViews, self).tearDown()

	def _get_link_by_rel(self, links, rel_name):
		return next((x for x in links if x.rel == rel_name))

	@WithMockDSTrans
	def test_unauthenticated_ping(self):
		result = ping(get_current_request())
		assert_that(result, has_property('links', has_length(greater_than_or_equal_to(6))))
		__traceback_info__ = result.links

		handshake_link = self._get_link_by_rel(result.links, 'logon.handshake')
		create_link = self._get_link_by_rel(result.links, 'account.create')
		assert_that(handshake_link.target, ends_with('/dataserver2/logon.handshake'))
		assert_that(create_link.target, ends_with('/dataserver2/account.create'))
		assert_that(create_link.target_mime_type, is_('application/vnd.nextthought.user'))
		external = to_external_object(result)

		assert_that(external, has_entry('AuthenticatedUsername', None))
		assert_that(external, has_entry('AuthenticatedUserId', None))

	@WithMockDSTrans
	def test_authenticated_ping(self):
		user = users.User.create_user(dataserver=self.ds, username='jason.madden@nextthought.com')
		class Policy(object):
			interface.implements(pyramid.interfaces.IAuthenticationPolicy)
			def authenticated_userid(self, request):
				return 'jason.madden@nextthought.com'
			def effective_principals(self, request):
				return [user]

		get_current_request().registry.registerUtility(Policy())

		result = ping(get_current_request())

		assert_that(result, has_property('links', has_length(greater_than_or_equal_to(3))))

		__traceback_info__ = result.links
		len_links = len(result.links)
		# assert_that( result.links[0].target, ends_with( '/dataserver2/handshake' ) )
		# assert_that( result.links[1].target, ends_with( '/dataserver2' ) )

		# We can increase that by adding links
		user_link_provider.add_link(user, 'force-edit-profile')
		result = ping(get_current_request())
		assert_that(result, has_property('links', has_length(len_links + 1)))
		external = to_external_object(result)
		assert_that(external, has_entry('Links', has_length(len_links + 1)))
		assert_that(external['Links'], has_item(has_entry('rel', 'force-edit-profile')))

		# Our external object also has the AuthenticatedUsername we expect
		assert_that(external, has_entry('AuthenticatedUsername', 'jason.madden@nextthought.com'))
		assert_that(external, has_entry('AuthenticatedUserId', not_(None)))

		# and we can decrease again
		user_link_provider.delete_link(user, 'force-edit-profile')
		result = ping(get_current_request())
		assert_that(result, has_property('links', has_length(len_links)))

	@WithMockDSTrans
	def test_fake_authenticated_handshake(self):
		# A user that doesn't actually exist.
		# Per current policy, the first link will be the generic password login
		class Policy(object):
			interface.implements(pyramid.interfaces.IAuthenticationPolicy)
			def authenticated_userid(self, request):
				return 'jason.madden@nextthought.com'
			def effective_principals(self, request):
				return [self.authenticated_userid(request)]

		component.provideUtility(Policy())

		get_current_request().params['username'] = 'jason.madden@nextthought.com'

		result = handshake(get_current_request())
		assert_that(result, has_property('links', has_length(greater_than_or_equal_to(3))))
		__traceback_info__ = result.links

		facebook_link = self._get_link_by_rel(result.links, 'logon.facebook')
		assert_that(facebook_link.target, is_('/dataserver2/logon.facebook1?username=jason.madden%40nextthought.com'))

	@WithMockDSTrans
	def test_handshake_no_user(self):
		# No username param
		result = handshake(get_current_request())

		password_link = self._get_link_by_rel(result.links, 'logon.nti.password')
		assert_that(password_link.target, starts_with('/dataserver2/logon.nti.password'))

	@WithMockDSTrans
	def test_handshake_existing_user_with_pass(self):
		# Clean up routes we don't yet want
		for route_name in ('logon.openid', 'logon.facebook.oauth1', 'logon.forgot.passcode', 'logon.forgot.username'):
			route = component.getUtility(pyramid.interfaces.IRouteRequest, name=route_name)
			__traceback_info__ = route_name, route
			assert component.globalSiteManager.unregisterUtility(route, provided=pyramid.interfaces.IRouteRequest, name=route_name)

		user = users.User.create_user(self.ds, username='jason.madden@nextthought.com', password='temp001')

		get_current_request().params['username'] = 'jason.madden@nextthought.com'

		# Give us the capability to do a google logon, and we can
		self.config.add_route(name='logon.google', pattern='/dataserver2/logon.google')
		result = handshake(get_current_request())
		assert_that(result, has_property('links', has_length(greater_than_or_equal_to(7))))
		__traceback_info__ = result.links

		pw_link = self._get_link_by_rel(result.links, 'logon.nti.password')
		assert_that(pw_link.target, contains_string('/dataserver2/logon.nti.password?'))

		# Give us a specific identity_url, and that changes to open id
		self.config.add_route(name='logon.openid', pattern='/dataserver2/logon.openid')
		user.identity_url = 'http://google.com/foo'
		interface.alsoProvides(user, nti_interfaces.IOpenIdUser)
		result = handshake(get_current_request())
		assert_that(result, has_property('links', has_length(greater_than_or_equal_to(7))))
		__traceback_info__ = result.links

		pw_link = self._get_link_by_rel(result.links, 'logon.nti.password')
		openid_link = self._get_link_by_rel(result.links, 'logon.openid')
		assert_that(pw_link.target, is_('/dataserver2/logon.nti.password?username=jason.madden%40nextthought.com'))
		assert_that(openid_link.target, contains_string('/dataserver2/logon.openid?'))
		assert_that(openid_link.target, contains_string('username=jason.madden%40nextthought.com'))
		assert_that(openid_link.target, contains_string('oidcsum=1290829754'))
		assert_that(openid_link.target, contains_string('openid=http'))

	def test_openid_login(self):
		fail = openid_login(None, get_current_request())
		assert_that(fail, is_(hexc.HTTPUnauthorized))

		from pyramid.session import SignedCookieSessionFactory
		my_session_factory = SignedCookieSessionFactory('ntidataservercookiesecretpass',
													httponly=True, serializer=JSONSerializer())
		self.config.set_session_factory(my_session_factory)
		self.config.add_route(name=ROUTE_OPENID_RESPONSE, pattern='/dataserver2/' + ROUTE_OPENID_RESPONSE)

		# TODO: This test is assuming we have access to google.com
		get_current_request().params['oidcsum'] = '1234'
		# XXX: This test fails when run by zope.testrunner. Why? It works fine in nose
		self.log_handler.add('pyramid_openid.view')

		# An openid request to a non-existant domain will fail
		# to begin negotiation
		get_current_request().params['openid'] = 'http://localhost/oidprovider/'
		result = openid_login(None, get_current_request())
		assert_that(result, is_(hexc.HTTPUnauthorized))
		assert_that(result.headers, has_key('Warning'))

	def test_password_logon_failed(self):
		self.beginRequest(request_factory=pyramid.request.Request.blank, request_args=('/',))
		class Policy(object):
			interface.implements(pyramid.interfaces.IAuthenticationPolicy)
			def forget(self, request):
				return [("Policy", "Me")]
			def authenticated_userid(self, request): return None
		component.provideUtility(Policy())
		# get_current_request().registry.registerUtility( Policy() )
		result = password_logon(get_current_request())
		assert_that(result, is_(hexc.HTTPUnauthorized))
		assert_that(result.headers, has_entry("Policy", "Me"))

		# Or a redirect
		self.beginRequest(request_factory=pyramid.request.Request.blank, request_args=('/?failure=/the/url/to/go/to',))
		# get_current_request().registry.registerUtility( Policy() )
		# get_current_request().params['failure'] = '/the/url/to/go/to'
		result = password_logon(get_current_request())
		assert_that(result, is_(hexc.HTTPSeeOther))
		assert_that(result.headers, has_entry("Policy", "Me"))
		assert_that(result, has_property('location', '/the/url/to/go/to'))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=False)
	def test_password_logon_success(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.create_user(self.ds, username='jason.madden@nextthought.com', password='temp001')

			class Policy(object):
				interface.implements(pyramid.interfaces.IAuthenticationPolicy)
				def remember(self, request, who):
					return [("Policy", who)]
				def authenticated_userid(self, request):
					return 'jason.madden@nextthought.com'
				def effective_principals(self, request):
					return [self.authenticated_userid(request)]

			get_current_request().registry.registerUtility(Policy())
			result = password_logon(get_current_request())
			assert_that(result, is_(hexc.HTTPNoContent))
			assert_that(result.headers, has_entry("Policy", 'jason.madden@nextthought.com'))

			# The event fired
			assert_that(user.lastLoginTime,
						is_(greater_than(0)))
			# Verify we have our first_time_logon flag (that is then deleted)
			assert_that(user_link_provider.has_link(user, 'first_time_logon'),
						is_(True))
		testapp = TestApp(self.app)
		testapp.delete('/dataserver2/users/jason.madden@nextthought.com/@@NamedLinks/first_time_logon',
						extra_environ=self._make_extra_environ('jason.madden@nextthought.com'),
						status=204)
		with mock_dataserver.mock_db_trans(self.ds):
			assert_that(user_link_provider.has_link(user, 'first_time_logon'),
						is_(False))

		# Or a redirect
		with mock_dataserver.mock_db_trans(self.ds):
			get_current_request().params['success'] = '/the/url/to/go/to'
			result = password_logon(get_current_request())
			assert_that(result, is_(hexc.HTTPSeeOther))
			assert_that(result.headers, has_entry("Policy", 'jason.madden@nextthought.com'))
			assert_that(result, has_property('location', '/the/url/to/go/to'))

	@WithMockDSTrans
	def test_policy_links(self):

		class Policy(object):
			interface.implements(pyramid.interfaces.IAuthenticationPolicy)
			def remember(self, request, who):
				return [("Policy", who)]
			def authenticated_userid(self, request):
				return 'zachary.roux@nextthought.com'
			def effective_principals(self, request):
				return [self.authenticated_userid(request)]

		get_current_request().registry.registerUtility(Policy())
		get_current_request().params['username'] = 'zachary.roux@nextthought.com'
		users.User.create_user(self.ds, username='zachary.roux@nextthought.com', password='temp001')
		result = handshake(get_current_request())

		tos_link = self._get_link_by_rel(result.links, 'content.direct_tos_link')
		assert_that(tos_link.target, equal_to(logon.TOS_URL))
		privacy_link = self._get_link_by_rel(result.links, 'content.direct_privacy_link')
		assert_that(privacy_link.target, equal_to(logon.PRIVACY_POLICY_URL))

	@WithMockDSTrans
	def test_create_openid_from_external(self):
		eventtesting.clearEvents()
		del _user_created_events[:]
		user = logon._deal_with_external_account(request=get_current_request(),
												  username="jason.madden@nextthought.com",
												  fname="Jason",
												  lname="Madden",
												  email="jason.madden@nextthought.com",
												  idurl="http://example.com",
												  iface=nti_interfaces.IOpenIdUser,
												  user_factory=users.OpenIdUser.create_user)
		assert_that(user, provides(nti_interfaces.IOpenIdUser))
		assert_that(user, is_(users.OpenIdUser))
		assert_that(user, has_property('identity_url', 'http://example.com'))
		assert_that(user_interfaces.IUserProfile(user), has_property('realname', 'Jason Madden'))
		assert_that(user_interfaces.IUserProfile(user), has_property('email', 'jason.madden@nextthought.com'))

		# The creation of this user caused events to fire
		assert_that(eventtesting.getEvents(), has_length(greater_than_or_equal_to(1)))

		assert_that(_user_created_events, has_length(1))
		assert_that(_user_created_events[0][0], is_(same_instance(user)))
		# We created a new user during a request, so that event fired
		assert_that(eventtesting.getEvents(app_interfaces.IUserCreatedWithRequestEvent), has_length(1))

		# Can also auth as facebook for the same email address
		# TODO: Think about that

		fb_user = logon._deal_with_external_account(request=get_current_request(),
													 username="jason.madden@nextthought.com",
													 fname="Jason",
													 lname="Madden",
													 email="jason.madden@nextthought.com",
													 idurl="http://facebook.com",
													 iface=nti_interfaces.IFacebookUser,
													 user_factory=users.FacebookUser.create_user)

		assert_that(fb_user, is_(same_instance(user)))
		assert_that(fb_user, provides(nti_interfaces.IFacebookUser))
		assert_that(fb_user, has_property('facebook_url', 'http://facebook.com'))

		# We have fired modified events for the addition of the interface
		# and the change of the URL
		mod_events = eventtesting.getEvents(IObjectModifiedEvent, lambda evt: evt.object == fb_user)
		assert_that(mod_events, has_length(1))
		assert_that(mod_events[0], has_property('object', fb_user))
		assert_that(mod_events[0].descriptions, has_item(has_property('attributes', has_item('facebook_url'))))

		# But the created-with-request did not fire
		assert_that(eventtesting.getEvents(app_interfaces.IUserCreatedWithRequestEvent), has_length(1))

	@WithMockDSTrans
	def test_create_facebook_from_external(self):
		eventtesting.clearEvents()
		del _user_created_events[:]
		fb_user = logon._deal_with_external_account(request=get_current_request(),
													username="jason.madden@nextthought.com",
													fname="Jason",
													lname="Madden",
													email="jason.madden@nextthought.com",
													idurl="http://facebook.com",
													iface=nti_interfaces.IFacebookUser,
													user_factory=users.FacebookUser.create_user)

		assert_that(fb_user, provides(nti_interfaces.IFacebookUser))
		assert_that(fb_user, has_property('facebook_url', 'http://facebook.com'))

		# The creation of this user caused events to fire
		assert_that(eventtesting.getEvents(), has_length(greater_than_or_equal_to(1)))

		assert_that(_user_created_events, has_length(1))
		assert_that(_user_created_events[0][0], is_(same_instance(fb_user)))

		# We created a new user during a request, so that event fired
		assert_that(eventtesting.getEvents(app_interfaces.IUserCreatedWithRequestEvent), has_length(1))

	@WithMockDSTrans
	def test_external_takes_realname(self):
		fb_user = logon._deal_with_external_account(request=get_current_request(),
													username="jason.madden@nextthought.com",
													fname="Jason",
													lname="Madden",
													email="jason.madden@nextthought.com",
													idurl="http://facebook.com",
													iface=nti_interfaces.IFacebookUser,
													user_factory=users.FacebookUser.create_user,
													realname='JA Madden')


		names = IFriendlyNamed(fb_user)
		assert_that(names.realname, is_('JA Madden'))

	@WithMockDSTrans
	def test_create_from_external_bad_data(self):
		with assert_raises(hexc.HTTPError):
			logon._deal_with_external_account(request=get_current_request(),
											  username="jason.madden@nextthought.com",
											  fname="Jason",
											  lname="Madden",
											  email="jason.madden_nextthought_com",  # Bad email
											  idurl="http://facebook.com",
											  iface=nti_interfaces.IFacebookUser,
											  user_factory=users.FacebookUser.create_user)

from zope.lifecycleevent.interfaces import IObjectCreatedEvent, IObjectModifiedEvent

_user_created_events = []
@component.adapter(nti_interfaces.IUser, IObjectCreatedEvent)
def _handle_user_create_event(user, object_added):
	_user_created_events.append((user, object_added))
