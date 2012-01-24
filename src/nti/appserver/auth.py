#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )
import warnings

from nti.dataserver.users import User

from authkit.authenticate import AddToEnviron, HTTPExceptionHandler
from authkit.authenticate.basic import make_basic_auth_handler
from authkit.users import UsersReadOnly

import os

class _NTIUsers(UsersReadOnly):

	def __init__( self, user_callable, create_user_callable=None ):
		"""
		:param user_callable: A function of username that returns a User object.
		"""
		super(_NTIUsers, self).__init__(None)
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
		return super(_NTIUsers,self).user_has_password( username, password )

def _make_user_auth(server):
	""" :return: Function to be used with authkit authentication. Function must be run in transaction. """

	def get_user( username ):
		return User.get_user( username, dataserver=server )

	create_user = None
	if 'DATASERVER_NO_AUTOCREATE_USERS' not in os.environ:
		def create( username ):
			warnings.warn( 'Autocreation of users is deprecated', FutureWarning )
			origuser = username
			if '@' not in username:
				username = username + '@nextthought.com'
			user = User.create_user( dataserver=server, username=username )
			server.root['users'][origuser] = user
			return user
		create_user = create


	users = _NTIUsers( get_user, create_user )

	def user_f( *args ):
		return users

	return user_f

class DecodeBasicUsername(object):
	"""
	Decodes %40 in a Basic Auth username into an @.

	Our usernames are in domain syntax. This sometimes confuses
	browsers who expect to use an @ to separate user and password,
	so clients often workaround this by percent-encoding the username.
	Reverse that step here. This should be an outer layer before
	authkit gets to do anything.
	"""

	def __init__( self, app ):
		self.app = app

	def __call__( self, environ, start_response ):
		authorization = environ.get( 'HTTP_AUTHORIZATION' )
		if authorization:
			(authmeth, auth) = authorization.split(' ',1)
			if 'basic' == authmeth.lower():
				auth = auth.strip().decode('base64')
				username, password = auth.split(':',1)
				username = username.replace( '%40', '@' )
				auth = (username + ':' + password).encode( 'base64' ).strip()
				environ['HTTP_AUTHORIZATION'] = 'Basic ' + auth
		return self.app( environ, start_response )



def add_authentication( application, server ):
	"""
	Given a WSGI application and a dataserver, wraps the
	application in the code required to do AuthKit authentication.
	This means that it catches all responses that come back with a status of 401
	and inserts WWW-Authenticate headers.
	:return: The wrapped application.
	"""

	user_f = _make_user_auth( server )

	application = HTTPExceptionHandler( application )
	application = make_basic_auth_handler( application, {'authenticate.user.type':user_f,'authenticate.user.data':None} )
	application = AddToEnviron( application, 'authkit.config', {'setup.enable':True})
	# NOTE: For this to work with pyramid, we must be catching
	# the 403 Forbidden exceptions it prefers to generate due to ACL walking
	# and transform them into 401s if authentication was bade--we cannot ask AuthKit to intercept all 403s,
	# as some of them are legitimate
	intercept = ['401']
	application = AddToEnviron( application, 'authkit.intercept', intercept )
	application = DecodeBasicUsername( application )


	return application


