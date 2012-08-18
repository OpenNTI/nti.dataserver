#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals


import binascii
import logging

from pyramid.interfaces import IAuthenticationPolicy

from zope import interface
from zope import component
from repoze.who.interfaces import IAuthenticator
from repoze.who.middleware import PluggableAuthenticationMiddleware
from repoze.who.plugins.basicauth import BasicAuthPlugin
from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.who.classifiers import default_challenge_decider
from repoze.who.classifiers import default_request_classifier
from pyramid_who.whov2 import WhoV2AuthenticationPolicy

from nti.dataserver.users import User
from nti.dataserver import authentication as nti_authentication

# TODO: This decoding stuff is happening too simalarly in the different
# places. Decide what's really needed and remove what isn't and consolidate
# the rest.

def _get_basicauth_credentials( request ):
	"""
	Check the request for credentials.

	:return: Tuple (user,pass) if present and valid in the
		request. Does not modify the request.
	"""
	username = None
	password = None
	try:
		authorization = request.authorization
		authmeth, auth = authorization
		if 'basic' == authmeth.lower():
			auth = auth.strip().decode('base64')
			username, password = auth.split(':',1)
	except (TypeError,ValueError, binascii.Error): username, password = None, None

	return (username, password)

def _get_basicauth_credentials_environ( environ ):
	"""
	Check the environment for credentials.

	:return: Tuple (user,pass) if present and valid in the
		request. Does not modify the request.
	"""
	username = None
	password = None
	try:
		authorization = environ['HTTP_AUTHORIZATION']
		authmeth, auth = authorization
		if 'basic' == authmeth.lower():
			auth = auth.strip().decode('base64')
			username, password = auth.split(':',1)
	except (TypeError,ValueError, binascii.Error): username, password = None, None

	return (username, password)

def _get_username( username ):
	if username:
		if '%40' in username:
			username = username.replace( '%40', '@' )
		username = username.lower() # Canonicalize the username
	return username

def _decode_username( request ):
	"""
	Decodes %40 in a Basic Auth username into an @. Modifies
	the request.

	Our usernames are in domain syntax. This sometimes confuses
	browsers who expect to use an @ to separate user and password,
	so clients often workaround this by percent-encoding the username.
	Reverse that step here. This should be an outer layer before
	authkit gets to do anything.

	:return: Tuple (user,pass).
	"""
	username, password = _get_basicauth_credentials( request )
	if _get_username( username ) != username:
		username = _get_username( username )
		auth = (username + ':' + password).encode( 'base64' ).strip()
		request.authorization = 'Basic ' + auth
		request.remote_user = username
	return (username, password)

def _decode_username_environ( environ ):
	"""
	Decodes %40 in a Basic Auth username into an @. Modifies
	the request.

	Our usernames are in domain syntax. This sometimes confuses
	browsers who expect to use an @ to separate user and password,
	so clients often workaround this by percent-encoding the username.
	Reverse that step here. This should be an outer layer before
	authkit gets to do anything.

	:return: Tuple (user,pass).
	"""
	username, password = _get_basicauth_credentials_environ( environ )
	if _get_username( username ) != username:
		username = _get_username( username )
		auth = (username + ':' + password).encode( 'base64' ).strip()
		environ['HTTP_AUTHORIZATION'] = 'Basic ' + auth
		environ['REMOTE_USER'] = username
	return (username, password)

def _decode_username_identity( identity ):
	"""
	Decodes %40 in a Basic Auth username into an @. Modifies
	the request.

	Our usernames are in domain syntax. This sometimes confuses
	browsers who expect to use an @ to separate user and password,
	so clients often workaround this by percent-encoding the username.
	Reverse that step here. This should be an outer layer before
	authkit gets to do anything.

	:return: Tuple (user,pass).
	"""
	username, password = identity['login'], identity['password']
	if _get_username( username ) != username:
		username = _get_username( username )
		identity['login'] = username
	return (username, password)

class _NTIUsers(object):

	def user_exists( self, username ):
		if not username or not username.strip(): # username is not None and not empty
			return False
		user = User.get_user( username )
		return user is not None

	def user_password( self, username ):
		userObj = User.get_user( username )
		return userObj.password if userObj else None

	def user_has_password( self, username, password ):
		if not self.user_exists( username ): return False
		user_password = self.user_password( username )
		return user_password.checkPassword( password ) if user_password else False

	def _query_groups( self, username, components ):
		":return: The groups of an authenticated user."
		return nti_authentication.effective_principals( username, registry=components, authenticated=True )

	def __call__( self, userid, request ):
		result = None
		# Because we are both part of a middleware and the pyramid
		# auth policy, we can get called both already authenticated
		# and not-authenticated.
		# TODO: Cache the groups results
		if 'repoze.who.userid' in userid:
			result = self._query_groups( userid['repoze.who.userid'], request.registry )
		elif 'login' in userid and 'password' in userid:
			username, password = _decode_username_identity( userid )
			if self.user_has_password( username, password ):
				result = self._query_groups( username, component )

		return result

def _make_user_auth():
	""" :return: Function to be used with authkit authentication. Function must be run in transaction. """

	# In the past, we passed _NTIUSers a
	# function that automatically created new user accounts, and this was enabled
	# by default. That's dangerous and is now disabled.
	return _NTIUsers( )

@interface.implementer( IAuthenticator )
class NTIUsersAuthenticatorPlugin(object):


	def authenticate( self, environ, identity ):
		if 'login' not in identity or 'password' not in identity:
			return None
		_decode_username_environ( environ )
		_decode_username_identity( identity )
		if _make_user_auth().user_has_password( identity['login'], identity['password'] ):
			return identity['login']

def _create_middleware( app=None ):
	user_auth = NTIUsersAuthenticatorPlugin()
	basicauth = BasicAuthPlugin('NTI')
	# Note that the cookie name needs to be bytes, not unicode. Otherwise we wind up with
	# unicode objects in the headers, which are supposed to be ascii. Things like the Cookie
	# module (used by webtest) then fail
	auth_tkt = AuthTktCookiePlugin('secret', b'nti.auth_tkt', timeout=30*24*60*60, reissue_time=600)
	# For testing, we let basic-auth set cookies. We don't want to do this
	# generally.
	#basicauth.include_ip = False
	#basicauth.remember = auth_tkt.remember

	# Identity (username) can come from the cookie,
	# or HTTP Basic auth
	identifiers = [('auth_tkt', auth_tkt),
				   ('basicauth', basicauth)]
	# Confirmation/authentication can come from the cookie (encryption)
	# Or possibly HTTP Basic auth
	authenticators = [('auth_tkt', auth_tkt),
					  ('htpasswd', user_auth)]
	challengers = [('basicauth', basicauth)]
	mdproviders = []

	middleware = PluggableAuthenticationMiddleware(
					app,
					identifiers,
					authenticators,
					challengers,
					mdproviders,
					default_request_classifier,
					default_challenge_decider,
					log_stream=logging.getLogger( 'repoze.who' ),
					log_level=logging.DEBUG )
	return middleware

def create_authentication_policy( ):
	middleware = _create_middleware()
	result = NTIAuthenticationPolicy()
	result.api_factory = middleware.api_factory
	# And make it capable of impersonation
	result = nti_authentication.DelegatingImpersonatedAuthenticationPolicy( result )
	return result

@interface.implementer( IAuthenticationPolicy )
class NTIAuthenticationPolicy(WhoV2AuthenticationPolicy):

	def __init__( self ):
		# configfile is ignored, second argument is identifier_id, which must match one of the
		# things we setup in _create_middleware. It's used in remember()
		super(NTIAuthenticationPolicy,self).__init__( '', 'auth_tkt', callback=_make_user_auth() )
		self.api_factory = None

	def unauthenticated_userid( self, request ):
		_decode_username( request )
		return super(NTIAuthenticationPolicy,self).unauthenticated_userid( request )

	def remember(self, request, principal, **kw):
		# The superclass hardcodes the dictionary that is used
		# for the identity. This identity is passed to the plugins.
		# The AuthTkt plugin will only set cookie expiration headers right
		# if a max_age is included in the identity.
		# So we force that here.
		api = self._getAPI(request)
		identity = {
			'repoze.who.userid': principal,
			'identifier': api.name_registry[self._identifier_id],
			'max_age': str(30*24*60*60)
			}
		return api.remember(identity)

	def _getAPI( self, request ):
		return self.api_factory( request.environ )
