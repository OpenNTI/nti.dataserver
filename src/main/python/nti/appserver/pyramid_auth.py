#!/usr/bin/env python2.7
import os
import binascii
import warnings
import logging

#from pyramid.authentication import CallbackAuthenticationPolicy
from paste.httpheaders import WWW_AUTHENTICATE
from repoze.who.interfaces import IAuthenticator, IChallengeDecider
from pyramid.interfaces import IAuthenticationPolicy

from zope import interface

from nti.dataserver.users import User


def _get_basicauth_credentials( request ):
	"""
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
	if username and '%40' in username:
		username = username.replace( '%40', '@' )
		auth = (username + ':' + password).encode( 'base64' ).strip()
		request.authorization = 'Basic ' + auth
		request.remote_user = username
	return (username, password)

class _NTIUsers(object):

	def __init__( self, user_callable, create_user_callable=None ):
		"""
		:param user_callable: A function of username that returns a User object.
		"""
		super(_NTIUsers, self).__init__()
		self.users = user_callable
		self.create = create_user_callable

	def user_exists( self, username ):
		if not username or not username.strip(): # username is not None and not empty
			return False
		user = self.users( username )
		if not user and self.create:
			self.create( username )
			user = self.users( username )
		return user is not None

	def user( self, username ):
		if not self.user_exists( username ): return None
		userObj = self.users( username )
		return {
			'username': username,
			'password': userObj.password,
			'roles': [],
			'group': None } if userObj else None

	def user_password( self, username ):
		if not self.user_exists( username ): return None
		userObj = self.user( username )
		return userObj['password'] if userObj else None

	def user_has_password( self, username, password ):
		if not username or not password or not username.strip() or not password.strip(): return False
		if not self.user_exists( username ): return False
		return password == self.user_password( username )

	def __call__( self, userid, request ):
		result = None
		# Because we are both part of a middleware and the pyramid
		# auth policy, we can get called both already authenticated
		# and not-authenticated.
		if 'login' in userid and 'password' in userid:
			username, password = userid['login'], userid['password'] # _decode_username( request )
			if self.user_has_password( username, password ):
				result = ()
		elif 'repoze.who.userid' in userid:
			result = ()
		return result

def _make_user_auth():
	""" :return: Function to be used with authkit authentication. Function must be run in transaction. """

	create_user = None
	if 'DATASERVER_NO_AUTOCREATE_USERS' not in os.environ:
		def create( username ):
			warnings.warn( 'Autocreation of users is deprecated', FutureWarning )
			#origuser = username
			if username and '@' not in username:
				warnings.warn( 'Usernames must contain "@"', FutureWarning )
				username = username + '@nextthought.com'
			user = User.create_user( username=username )
			#server.root['users'][origuser] = user
			return user
		create_user = create

	return _NTIUsers( User.get_user, create_user )

pyramid_auth_callback = _make_user_auth

class NTIUsersAuthenticatorPlugin(object):
	interface.implements( IAuthenticator )

	def __init__( self ):
		pass

	def authenticate( self, environ, identity ):
		if 'login' not in identity or 'password' not in identity: return None

		if _make_user_auth().user_has_password( identity['login'], identity['password'] ):
			return identity['login']

from repoze.who.middleware import PluggableAuthenticationMiddleware
from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IChallenger
from repoze.who.plugins.basicauth import BasicAuthPlugin
from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.who.plugins.redirector import RedirectorPlugin
from repoze.who.plugins.htpasswd import HTPasswdPlugin
from repoze.who.classifiers import default_challenge_decider
from repoze.who.classifiers import default_request_classifier
from pyramid_who.whov2 import WhoV2AuthenticationPolicy

def _basicauth_challenge_decider( environ, status, headers ):
	"""
	Transform the 403 Forbidden response into a 401 Unauthorized
	response if there are no credentials provided.
	"""
	return (status.startswith( '403' ) and 'repoze.who.identity' not in environ) \
		   or default_challenge_decider( environ, status, headers )

interface.directlyProvides( _basicauth_challenge_decider, IChallengeDecider )

def _create_middleware( app=None ):
	user_auth = NTIUsersAuthenticatorPlugin()
	basicauth = BasicAuthPlugin('NTI')
	auth_tkt = AuthTktCookiePlugin('secret', 'auth_tkt')
	basicauth.include_ip = False
	basicauth.remember = auth_tkt.remember
	identifiers = [('auth_tkt', auth_tkt),
				   ('basicauth', basicauth)]
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
					_basicauth_challenge_decider,
					log_stream = logging.getLogger( 'repoze.who' ),
					log_level = logging.DEBUG )
	return middleware

def wrap_repoze_middleware( app ):
	return _create_middleware( app )

def create_authentication_policy( ):
	middleware = _create_middleware()
	result = NTIAuthenticationPolicy()
	result.api_factory = middleware.api_factory
	return result

class NTIAuthenticationPolicy(WhoV2AuthenticationPolicy):

	interface.implements( IAuthenticationPolicy )

	def __init__( self ):
		super(NTIAuthenticationPolicy,self).__init__( '', '', callback=_make_user_auth() )
		self.api_factory = None

	def unauthenticated_userid( self, request ):
		_decode_username( request )
		return super(NTIAuthenticationPolicy,self).unauthenticated_userid( request )

	def _getAPI( self, request ):
		return self.api_factory( request.environ )
