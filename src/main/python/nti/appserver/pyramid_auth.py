#!/usr/bin/env python2.7
import os
import binascii
import warnings

from pyramid.authentication import CallbackAuthenticationPolicy
from paste.httpheaders import WWW_AUTHENTICATE
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
	if username and '@' in username:
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
		username, password = _decode_username( request )
		if self.user_has_password( username, password ):
			return ()
		return None

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

class NTIBasicAuthPolicy(CallbackAuthenticationPolicy):

	interface.implements( IAuthenticationPolicy )

	def __init__( self, realm='NTI' ):
		super(NTIBasicAuthPolicy,self).__init__( )
		self.callback = _make_user_auth()
		self.realm = realm
		self.users = None

	def unauthenticated_userid( self, request ):
		return _decode_username( request )[0]

	def remember(self, request, principal, **kw):
		# TODO: Set authtkt token?
		return []

	def forget(self, request):
		head = WWW_AUTHENTICATE.tuples('Basic realm="%s"' % self.realm)
		return head

from pyramid.httpexceptions import default_exceptionresponse_view, HTTPUnauthorized
import pyramid.security as sec

def exceptionresponse_view(context, request):
	"""
	Transform the 403 Forbidden response into a 401 Unauthorized
	response if there are no credentials provided.

	This is probably something of a hack. We're letting this exception
	propagate up to AuthKit, which renderes the response and
	inserts WWW-Authenticate. It's not clear how to make pyramid do
	this on its own.
	"""

	if getattr( context, 'code', 0 ) == 403:
		if not sec.authenticated_userid( request ):
			unauth = HTTPUnauthorized( detail=context.detail,
									   headers=context.headers,
									   comment=context.comment )
			context = unauth
	return default_exceptionresponse_view( context, request )

