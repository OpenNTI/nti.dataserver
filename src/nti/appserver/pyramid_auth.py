#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__ )

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

from pyramid_who.whov2 import WhoV2AuthenticationPolicy
from pyramid_who.classifiers import forbidden_challenger

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authentication as nti_authentication
from nti.dataserver import authorization as nti_authorization

from . import httpexceptions as hexc
from nti.app.renderers.caching import default_vary_on
from .interfaces import IUserViewTokenCreator
from nti.app.authentication.interfaces import ILogonWhitelist

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

from nti.app.authentication.who_authenticators import DataserverGlobalUsersAuthenticatorPlugin
from nti.app.authentication.who_authenticators import KnownUrlTokenBasedAuthenticator

from nti.app.authentication.interfaces import IIdentifiedUserTokenAuthenticator

@interface.implementer(IUserViewTokenCreator)
class _UserViewTokenCreator(object):

	def __init__(self, secret, allowed_views):
		self.secret = secret
		self.allowed_views = allowed_views

	def getTokenForUserId( self, userid ):
		"""
		Given a logon for a user, return a token that can be
		used to identify the user in the future. If the user
		does not exist or cannot get a token, return None.
		"""
		return component.getAdapter(self.secret,IIdentifiedUserTokenAuthenticator).getTokenForUserId(userid)

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
		ua = environ.get('HTTP_USER_AGENT', '').lower()
		# OK, but is it an programmatic browser request where we'd like to
		# change up the auth rules?
		if environ.get( 'HTTP_X_REQUESTED_WITH', '' ).lower() == b'xmlhttprequest':
			# An easy Yes!
			result = CLASS_BROWSER_APP
		elif environ.get('paste.testing') is True:
			result = environ.get('nti.paste.testing.classification', CLASS_BROWSER_APP )
		elif 'python' in ua or 'httpie' in ua:
			result = CLASS_BROWSER_APP
		else:
			# Hmm. Going to have to do some guessing. Sigh.
			# First, we sniff for something that looks like it's sent by
			# a true web browser, like Chrome or Firefox
			# Then, if there is an Accept value given other than the default that's
			# sent by user agents like, say, NetNewsWire, then it was probably
			# set programatically.
			if ('HTTP_REFERER' in environ
				 and 'mozilla' in ua
				 and environ.get('HTTP_ACCEPT', '') != '*/*'):
				result = CLASS_BROWSER_APP
	return result

from pyramid.interfaces import IRequest
@interface.implementer(IRequestClassifier)
@component.adapter(IRequest)
def _nti_request_classifier_for_request(request):
	return _nti_request_classifier


@interface.provider(IChallengeDecider)
def _nti_challenge_decider( environ, status, headers ):
	"""
	We want to offer an auth challenge (e.g., a 401 response) if
	Pyramid thinks we need one (by default, a 403 response) and if we
	have no credentials at all. (If we have credentials, then the
	correct response is a 403, not a challenge.)
	"""
	return 'repoze.who.identity' not in environ and forbidden_challenger( environ, status, headers )


def _create_who_apifactory( secure_cookies=True,
							cookie_secret='$Id$',
							cookie_timeout=ONE_WEEK,
							token_allowed_views=('feed.rss', 'feed.atom')):

	# Note that the cookie name and header names needs to be bytes,
	# not unicode. Otherwise we wind up with unicode objects in the
	# headers, which are supposed to be ascii. Things like the Cookie
	# module (used by webtest) then fail
	basicauth = BasicAuthPlugin(b'NTI')
	basicauth_interactive = _NonChallengingBasicAuthPlugin(b'NTI')

	def user_can_login(username):
		whitelist = component.getUtility(ILogonWhitelist)
		return username in whitelist and User.get_user(username) is not None

	auth_tkt = AuthTktCookiePlugin(cookie_secret,
								   b'nti.auth_tkt',
								   secure=secure_cookies,
								   timeout=cookie_timeout,
								   reissue_time=600,
								   # For extra safety, we can refuse to return authenticated ids
								   # if they don't exist or are denied logon. If we are called too early, outside the site,
								   # this can raise an exception, but the only place that matters, logging,
								   # already deals with it (gunicorn.py). Because it's an exception,
								   # it prevents any of the caching from kicking in
								   userid_checker=user_can_login)

	# Create a last-resort identifier and authenticator that
	# can be used only for certain views, here, our
	# known RSS/Atom views. This is clearly not very configurable.
	token_tkt = KnownUrlTokenBasedAuthenticator( cookie_secret,
												 allowed_views=token_allowed_views )

	# Claimed identity (username) can come from the cookie,
	# or HTTP Basic auth, or in special cases, from the token query param
	identifiers = [('auth_tkt', auth_tkt),
				   ('basicauth-interactive', basicauth_interactive),
				   ('basicauth', basicauth),
				   ('token_tkt', token_tkt)]
	# Confirmation/authentication can come from the cookie (encryption)
	# Or possibly HTTP Basic auth, or in special cases, from the
	# token query param
	authenticators = [('auth_tkt', auth_tkt),
					  ('htpasswd', DataserverGlobalUsersAuthenticatorPlugin()),
					  ('token_tkt', token_tkt)]
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

def create_authentication_policy( secure_cookies=True,
								  cookie_secret='$Id$',
								  cookie_timeout=ONE_WEEK ):
	"""
	:param bool secure_cookies: If ``True`` (the default), then any cookies
		we create will only be sent over SSL and will additionally have the 'HttpOnly'
		flag set, preventing them from being subject to cross-site vulnerabilities.
		This must be explicitly turned off if not desired.
	:param str cookie_secret: The value used to encrypt cookies. Must be the same on
		all instances in a given environment, but should be different in different
		environments.

	:return: A tuple of the authentication policy, and a forbidden
		view that must be installed to make it effective, and a :class:`.IUserViewTokenCreator`
		that should be registered as a named utility.
	"""
	token_allowed_views = ('feed.rss', 'feed.atom')
	api_factory = _create_who_apifactory(secure_cookies=secure_cookies,
										 cookie_secret=cookie_secret,
										 cookie_timeout=cookie_timeout,
										 token_allowed_views=token_allowed_views)
	result = NTIAuthenticationPolicy(cookie_timeout=cookie_timeout,api_factory=api_factory)
	# And make it capable of impersonation
	result = nti_authentication.DelegatingImpersonatedAuthenticationPolicy( result )
	return result, NTIForbiddenView(api_factory), _UserViewTokenCreator(cookie_secret, token_allowed_views)

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
			'max_age': str(self._cookie_timeout),
			# For the auth tkt to also be able to set REMOTE_USER_DATA
			# and REMOTE_USER_TOKENS, those also need to come in as
			# 'tokens' and 'userdata'. Ideally we would construct
			# those at some point during authentication and grab them from the
			# identity dict, but for now we simply re-echo what we have
			# The tokens is a tuple of (native) strings, while
			# userdata is a single string
			'tokens': request.environ.get('REMOTE_USER_TOKENS', ()),
			'userdata': request.environ.get('REMOTE_USER_DATA', b'')
			}
		return api.remember(identity)

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
