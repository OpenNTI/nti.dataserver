#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__ )

import binascii

from zope import interface
from zope import component

# Like Pyramid 1.4+, cause Paste's AuthTkt cookies to use the more secure
# SHA512 algorithm instead of the weaker MD5 (actually, repoze.who, now)
import nti.monkey.paste_auth_tkt_sha512_patch_on_import
nti.monkey.paste_auth_tkt_sha512_patch_on_import.patch()

from pyramid.interfaces import IAuthenticationPolicy

from repoze.who.api import APIFactory
from repoze.who.plugins.basicauth import BasicAuthPlugin
from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.who.classifiers import default_request_classifier
from repoze.who.interfaces import IAuthenticator, IIdentifier, IChallenger, IChallengeDecider, IRequestClassifier

from pyramid.request import Request
from pyramid_who.whov2 import WhoV2AuthenticationPolicy
from pyramid_who.classifiers import forbidden_challenger

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authentication as nti_authentication
from nti.dataserver import authorization as nti_authorization

from . import httpexceptions as hexc
from .pyramid_renderers import default_vary_on

def _decode_username_request( request ):
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

	authmeth, auth = request.authorization or ('','')
	if authmeth.lower() != b'basic':
		return (None,None)

	# Remember here we're working with byte headers
	try:
		username, password = auth.strip().decode('base64').split(b':',1)
	except (ValueError,binascii.Error): # pragma: no cover
		return (None,None)

	# we only get here with two strings, although either could be empty
	canonical_username = username.lower().replace( b'%40', b'@' ).strip() if username else username
	if canonical_username != username:
		username = canonical_username
		auth = (username + b':' + password).encode( 'base64' ).strip()
		request.authorization = (authmeth, auth)
		request.remote_user = username

	return (username, password)

class _NTIUsers(object):

	@classmethod
	def user_exists( cls, username ):
		if not username: #pragma: no cover # username is not None (not empty taken care of during decoding)
			return None
		user = User.get_user( username )
		return user is not None and user

	@classmethod
	def user_password( cls, username ):
		userObj = User.get_user( username )
		return userObj.password if userObj else None

	@classmethod
	def user_has_password( cls, username, password ):
		user = cls.user_exists( username )
		if not user or not password:
			return False
		user_password = user.password
		return user_password.checkPassword( password ) if user_password else False

	def _query_groups( self, username, components ):
		":return: The groups of an authenticated user."
		if not self.user_exists( username ): # pragma: no cover
			return None
		return nti_authentication.effective_principals( username, registry=components, authenticated=True )

	def __call__( self, identity, request ):
		"""
		Callback method for :mod:`pyramid_who`. We are guaranteed to
		only be called when an :class:`.IAuthenticator` has matched;
		we get the last say, as returning None from this callback
		causes :meth:`.authenticated_userid` to also return None.
		"""
		# NOTE: we are caching the group results as part of the userid dictionary,
		# which means they cannot change during a request.
		CACHE_KEY = 'nti.dataserver.groups'
		if CACHE_KEY in identity:
			return identity[CACHE_KEY]

		username = None
		if 'repoze.who.userid' in identity: # already identified by AuthTktCookie or _NTIUsersAuthenticatorPlugin
			username = identity['repoze.who.userid']

		result = None
		if self.user_exists( username ): # This should already have been checked, actually
			result = self._query_groups( username, request.registry )

		identity[CACHE_KEY] = result
		return result

@interface.implementer(IAuthenticator)
class _NTIUsersAuthenticatorPlugin(object):

	def authenticate( self, environ, identity ):
		try:
			if _NTIUsers.user_has_password( identity['login'], identity['password'] ):
				return identity['login']
		except KeyError: # pragma: no cover
			return None

class _KnownUrlTokenBasedAuthenticator(object):
	"""
	A :mod:`repoze.who` plugin that acts in the role of identifier
	(determining who the remote user is claiming to be)
	as well as authenticator (matching the claimed remote credentials
	to the real credentials). This information is not sent in the
	headers (Authenticate or Cookie) but instead, for the use of
	copy-and-paste, retrieved directly from query parameters in the
	URL (specifically, the 'token' parameter).

	This is similar in principal to the AuthTkt cookie we use
	in HTTP headers, but there is one crucial difference:
	the authtkt cookie is generally time limited (to mitigate damage due to a
	publicized cookie) but does not have any relationship to the
	user's password (the password can change, and existing tkts stay
	valid).

	In this case, we want the value to stay valid as long as possible.
	The user is being directly given this token and told to safeguard it,
	and to plug it into something they won't look at often (an RSS reader).
	So rather than using a timestamp value to mitigate damage due to a
	public token, we instead tie it to the password. If the user fears the
	password has been lost, he is advised to change the password.

	Because it is part of the URL, this information is visible in the
	logs for the entire HTTP pipeline. To limit the overuse of this, we
	only want to allow it for particular URLs, as based on the path.
	"""

	# We actually piggyback off the authtkt implementation, using
	# a version of the user's password as the 'user data'

	from repoze.who.plugins.auth_tkt import auth_tkt
	from paste.request import parse_dict_querystring
	parse_dict_querystring = staticmethod(parse_dict_querystring)
	from hashlib import sha256

	def __init__( self, secret, allowed_views=() ):
		"""
		Creates a combo :class:`.IIdentifier` and :class:`.IAuthenticator`
		using an auth-tkt like token.

		:param string secret: The encryption secret. May be the same as the
			auth_tkt secret.
		:param sequence allowed_views: A set of view names (final path sequences)
			that will be allowed to be authenticated by this plugin.
		"""
		self.secret = secret
		self.allowed_views = allowed_views

	def identify( self, environ ):
		# Obviously if there is no token we can't identify
		if b'QUERY_STRING' not in environ or b'token' not in environ[b'QUERY_STRING']:
			return
		if b'PATH_INFO' not in environ:
			return
		if not any((environ['PATH_INFO'].endswith(view) for view in self.allowed_views)):
			return

		query_dict = self.parse_dict_querystring( environ )
		token = query_dict['token']

		try:
			_, userid, tokens, user_data = self.auth_tkt.parse_ticket( self.secret,
																  token,
																  '0.0.0.0' )
		except self.auth_tkt.BadTicket: # pragma: no cover
			return None

		identity = {}
		identity['nti.pyramid_auth.token.userid'] = userid
		identity['nti.pyramid_auth.token.userdata'] = user_data
		return identity

	def forget(self, environ, identity): # pragma: no cover
		return []
	def remember(self, environ, identity): # pragma: no cover
		return []

	def authenticate(self, environ, identity):
		if 'nti.pyramid_auth.token.userid' not in identity:
			return None

		userid = identity['nti.pyramid_auth.token.userid']
		# This part is where the password tie-in is implemented.
		userdata = identity['nti.pyramid_auth.token.userdata']
		environ[b'AUTH_TYPE'] = b'token'
		# We would be storing hashed and salted password data for the
		# user, currently in bcrypt. Exposing the bcrypt hash and salt
		# is not a security problem, as the raw password cannot be obtained
		# from the bcrypt value (not in a feasible amount of time anyway),
		# and there is no entry point to the system that will accept the
		# raw bcrypt value and directly compare it to produce an authentication
		# result---the user must give the real password.
		#
		# That said, I'm not comfortable exposing it directly. Therefore, we
		# take *another* hash on top of that. This needs to be fast, unlike bcrypt,
		# because we produce and write out these tokens frequently.
		user_passwd = _NTIUsers.user_password( userid )
		if user_passwd:
			raw_data = user_passwd.getPassword()
			hexdigest = self.sha256( raw_data ).hexdigest()
			return  userid if hexdigest == userdata else None

		return None # No user or password has changed.

	def tokenForUserid( self, userid ):
		"""
		Given a logon for a user, return a token that can be
		used to identify the user in the future. If the user
		does not exist or cannot get a token, return None.
		"""

		user_pw = _NTIUsers.user_password( userid )
		if user_pw is None:
			return None

		raw_data = user_pw.getPassword()
		hexdigest = self.sha256( raw_data ).hexdigest()
		tkt = self.auth_tkt.AuthTicket(self.secret, userid, '0.0.0.0', user_data=hexdigest)
		return tkt.cookie_value()

@interface.implementer(IAuthenticator,IIdentifier)
class _FixedUserAuthenticatorPlugin(object): # pragma: no cover # For use with redbot testing

	username = 'pacifique.mahoro@nextthought.com'
	def authenticate(self, environ, identity ):
		return self.username

	def identify(self, environ):
		return {'login': self.username}

	def remember( self, *args ):
		return ()

	def forget(self, *args):
		return ()

ONE_DAY = 24 * 60 * 60
ONE_WEEK = 7 * ONE_DAY
ONE_MONTH = 30 * ONE_DAY

#: A request classification that is meant to indicate a browser
#: or browser-like environment being used programattically, i.e.,
#: a web-app request, as opposed to a pure, interactive human user
#: of the browser
CLASS_BROWSER_APP = 'application-browser'

class _NonChallengingBasicAuthPlugin(BasicAuthPlugin):
	"""
	For use when the request is probably an interactive XHR request, but
	credentials are totally invalid. We need to send a 401 response, but sending
	the WWW-Authenticate header probably causes a browser on the other end to
	pop-up a dialog box, which is no help. Technically, this violates the HTTP
	spec which requires a WWW-Authenticate header on a 401; but it seems safer to elide
	it then to create our own type?
	"""

	classifications = {IChallenger: [CLASS_BROWSER_APP],
					   IIdentifier: [CLASS_BROWSER_APP]}

	def challenge(self, environ, status, app_headers, forget_headers):
		exc = super(_NonChallengingBasicAuthPlugin,self).challenge( environ, status, app_headers, forget_headers )
		del exc.headers['WWW-Authenticate'] # clear out the WWW-Authenticate header
		return exc

	def forget(self, environ, identity):
		return ()

@interface.provider(IRequestClassifier)
def _nti_request_classifier( environ ):
	"""
	Extends the default classification scheme to try to detect
	requests in which the browser is being used by an application and we don't
	want to generate a native authentication dialog.
	"""

	result = default_request_classifier( environ )

	if result == 'browser':
		# OK, but is it an programmatic browser request where we'd like to
		# change up the auth rules?
		if environ.get( 'HTTP_X_REQUESTED_WITH', '' ).lower() == b'xmlhttprequest':
			# An easy Yes!
			result = CLASS_BROWSER_APP
		else:
			# Hmm. Going to have to do some guessing. Sigh.
			# First, we sniff for something that looks like it's sent by
			# a true web browser, like Chrome or Firefox
			# Then, if there is an Accept value given other than the default that's
			# sent by user agents like, say, NetNewsWire, then it was probably
			# set programatically
			if ('HTTP_REFERER' in environ
				 and 'Mozilla' in environ.get( 'HTTP_USER_AGENT', '' )
				 and environ.get('HTTP_ACCEPT', '') != '*/*'):
				result = CLASS_BROWSER_APP
	return result

@interface.provider(IChallengeDecider)
def _nti_challenge_decider( environ, status, headers ):
	"""
	We want to offer an auth challenge (e.g., a 401 response) if
	Pyramid thinks we need one (by default, a 403 response) and if we
	have no credentials at all. (If we have credentials, then the
	correct response is a 403, not a challenge.)
	"""
	return 'repoze.who.identity' not in environ and forbidden_challenger( environ, status, headers )


def _create_who_apifactory( secure_cookies=False,
							cookie_secret='secret',
							cookie_timeout=ONE_WEEK ):

	# Note that the cookie name and header names needs to be bytes,
	# not unicode. Otherwise we wind up with unicode objects in the
	# headers, which are supposed to be ascii. Things like the Cookie
	# module (used by webtest) then fail
	basicauth = BasicAuthPlugin(b'NTI')
	basicauth_interactive = _NonChallengingBasicAuthPlugin(b'NTI')

	auth_tkt = AuthTktCookiePlugin(cookie_secret,
								   b'nti.auth_tkt',
								   secure=secure_cookies,
								   timeout=cookie_timeout,
								   reissue_time=600,
								   # For extra safety, we can refuse to return authenticated ids
								   # if they don't exist. If we are called too early, outside the site,
								   # this can raise an exception, but the only place that matters, logging,
								   # already deals with it (gunicorn.py). Because it's an exception,
								   # it prevents any of the caching from kicking in
								   userid_checker=User.get_user)


	# Claimed identity (username) can come from the cookie,
	# or HTTP Basic auth
	identifiers = [('auth_tkt', auth_tkt),
				   ('basicauth-interactive', basicauth_interactive),
				   ('basicauth', basicauth)]
	# Confirmation/authentication can come from the cookie (encryption)
	# Or possibly HTTP Basic auth
	authenticators = [('auth_tkt', auth_tkt),
					  ('htpasswd', _NTIUsersAuthenticatorPlugin())]
	challengers = [ # Order matters when multiple classifications match
				   ('basicauth-interactive', basicauth_interactive),
				   ('basicauth', basicauth), ]
	mdproviders = []

	if False: # pragma: no cover # for redbot testing
		identifiers.insert( 0, ('fixed', _FixedUserAuthenticatorPlugin()) )
		authenticators.insert( 0, ('fixed', _FixedUserAuthenticatorPlugin()) )

	api_factory = APIFactory(identifiers,
							 authenticators,
							 challengers,
							 mdproviders,
							 _nti_request_classifier,
							 _nti_challenge_decider,
							 b'REMOTE_USER', # environment remote user key
							 None ) # No logger, leads to infinite loops

	return api_factory

def create_authentication_policy( secure_cookies=False, cookie_secret='secret', cookie_timeout=ONE_WEEK ):
	"""
	:param bool secure_cookies: If ``True`` (not the default), then any cookies
		we create will only be sent over SSL and will additionally have the 'HttpOnly'
		flag set, preventing them from being subject to cross-site vulnerabilities.
	:param str cookie_secret: The value used to encrypt cookies. Must be the same on
		all instances in a given environment, but should be different in different
		environments.
	:return: A tuple of the authentication policy, and a forbidden view that must be installed
		to make it effective.
	"""
	api_factory = _create_who_apifactory(secure_cookies=secure_cookies, cookie_secret=cookie_secret, cookie_timeout=cookie_timeout )
	result = NTIAuthenticationPolicy(cookie_timeout=cookie_timeout,api_factory=api_factory)
	# And make it capable of impersonation
	result = nti_authentication.DelegatingImpersonatedAuthenticationPolicy( result )
	return result, NTIForbiddenView(api_factory)

@interface.implementer(IAuthenticationPolicy)
class NTIAuthenticationPolicy(WhoV2AuthenticationPolicy):

	def __init__( self, cookie_timeout=ONE_WEEK, api_factory=None ):
		# configfile is ignored, second argument is identifier_id, which must match one of the
		# things we setup in _create_middleware. It's used in remember()
		super(NTIAuthenticationPolicy,self).__init__( '', 'auth_tkt', callback=_NTIUsers() )
		self._api_factory = api_factory
		self._cookie_timeout = cookie_timeout

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
			'max_age': str(self._cookie_timeout)
			}
		return api.remember(identity)

	def _getAPI( self, request ):
		environ = request.environ
		if 'repoze.who.identity' not in environ: # First time

			try:
				_decode_username_request( request )
			except AttributeError: # DummyRequest
				_decode_username_request( Request( environ ) )

		return self._api_factory( environ )

class NTIForbiddenView(object):
	"""
	Works with the configured `IChallengeDecider` and `IChallenger` to
	replace Pyramid's generic "403 Forbidden" with the proper
	challenge.

	Note that pyramid issues 403 forbidden even when no credentials
	are provided---which should instead be a 401, so this method does that.
	"""

	def __init__( self, api_factory ):
		self.api_factory = api_factory

	def __call__( self, request ):
		# TODO: This is very similar to some code in the PluggableAuthenticationMiddleware.
		# Should we just use that? It changes the order in which things are done, though
		# which might cause transaction problems?
		result = request.exception
		api = self.api_factory( request.environ )
		if api.challenge_decider(request.environ, request.exception.status, request.exception.headers):
			challenge_app = api.challenge(request.exception.status, request.exception.headers)
			if challenge_app is not None:
				# Although these generically can return "apps" that are supposed to be WSGI callables,
				# in reality they only return instances of paste.httpexceptions.HTTPClientError.
				# Which happens to map one-to-one to the pyramid exception framework
				result = hexc.__dict__[type(challenge_app).__name__](headers=challenge_app.headers)

		result.vary = default_vary_on( request ) # TODO: Do this with a response factory or something similar
		return result

@interface.implementer(nti_interfaces.IGroupMember)
@component.adapter(nti_interfaces.IUser)
class NextthoughtDotComAdmin(object):
	"""
	Somewhat hackish way to grant the admin role to any account in @nextthought.com
	"""

	def __init__( self, context ):
		self.groups = (nti_authorization.ROLE_ADMIN,) if context.username.endswith( '@nextthought.com' ) else ()
