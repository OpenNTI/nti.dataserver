#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views and data models relating to the login process.

Login begins with :func:`ping`, possibly proceeding to :func:`handshake` and
from there, depending on the user account type, to one of :func:`google_login`, :func:`facebook_oauth1`,
or :func:`password_login`.

A login session is terminated with :func:`logout`.

OpenID
======

Attribute exchange is used to collect permissions from providers. The
URI used as the `attribute type identifier <http://openid.net/specs/openid-attribute-exchange-1_0.html#attribute-name-definition>`_
is in :const:`AX_TYPE_CONTENT_ROLES`


Impersonation
=============

Impersonation is exposed at the url :const:`REL_LOGIN_IMPERSONATE`. See
the function :func:`impersonate_user` for more details.


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from . import MessageFactory as _

import logging
logger = logging.getLogger(__name__)
# Clean up the logging of openid, which writes to stderr by default. Patching
# the module like this is actually the recommended approach
import openid.oidutil
openid.oidutil.log = logging.getLogger('openid').info

from zope import interface
from zope import component
from zope import lifecycleevent
from zope.event import notify
from zope.i18n import translate

from nti.dataserver import interfaces as nti_interfaces
from nti.externalization import interfaces as ext_interfaces
from nti.appserver import interfaces as app_interfaces
from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver.links import Link
from nti.dataserver import mimetype
from nti.dataserver import users
from nti.dataserver import authorization as nauth

from nti.appserver._util import logon_userid_with_request
from nti.appserver.account_creation_views import REL_CREATE_ACCOUNT, REL_PREFLIGHT_CREATE_ACCOUNT
from nti.appserver.account_recovery_views import REL_FORGOT_USERNAME, REL_FORGOT_PASSCODE, REL_RESET_PASSCODE
from nti.appserver.pyramid_authorization import has_permission

from nti.ntiids import ntiids

from pyramid.view import view_config
from pyramid import security as sec
import pyramid.interfaces
import pyramid.request
import pyramid.httpexceptions as hexc

import logilab.common.cache
import requests
from requests.exceptions import RequestException

import urllib
import urlparse
import anyjson as json

#: Link relationship indicating a welcome page
#: Fetching the href of this link returns either a content page
#: or PageInfo structure. The client is expected to DELETE
#: this link once the user has viewed it.
REL_INITIAL_WELCOME_PAGE = "content.initial_welcome_page"

#: Link relationship indicating a welcome page
#: The client is expected to make this relationship
#: available to the end user at all times. It is NOT a deletable
#: link.
REL_PERMANENT_WELCOME_PAGE = 'content.permanent_welcome_page'


#: Link relationship indicating the Terms-of-service page
#: Fetching the href of this link returns either a content page
#: or PageInfo structure. The client is expected to DELETE
#: this link once the user has viewed it and accepted it.
REL_INITIAL_TOS_PAGE = "content.initial_tos_page"

#: Link relationship indicating a the Terms-of-service page
#: The client is expected to make this relationship
#: available to the end user at all times for review. It is NOT a deletable
#: link.
REL_PERMANENT_TOS_PAGE = 'content.permanent_tos_page'

REL_PING = 'logon.ping' #: See :func:`ping`
REL_HANDSHAKE = 'logon.handshake' #: See :func:`handshake`
REL_CONTINUE  = 'logon.continue'

REL_LOGIN_NTI_PASSWORD = 'logon.nti.password' #: See :func:`password_logon`
REL_LOGIN_IMPERSONATE = 'logon.nti.impersonate' #: See :func:`impersonate_user`
REL_LOGIN_GOOGLE = 'logon.google' #: See :func:`google_login`
REL_LOGIN_OPENID = 'logon.openid' #: See :func:`openid_login`
REL_LOGIN_FACEBOOK = 'logon.facebook' #: See :func:`facebook_oauth1`
REL_LOGIN_LOGOUT = 'logon.logout' #: See :func:`logout`

ROUTE_OPENID_RESPONSE = 'logon.openid.response'

#: The URI used as in attribute exchange to request the content to which
#: the authenticated entity has access. The attribute value type is defined
#: as a list of unlimited length, each entry of which refers to a specific
#: :class:`nti.contentlibrary.interfaces.IContentPackage`. Certain providers
#: may have special mapping rules, but in general, each entry is the specific local
#: part of the NTIID of that content package (and the provider is implied from the
#: OpenID domain). These will be turned into groups that the :class:`nti.dataserver.interfaces.IUser`
#: is a member of; see :class:`nti.dataserver.interfaces.IGroupMember` and :mod:`nti.dataserver.authorization_acl`.
#:
#: The NTIID of each content package thus referenced should be checked to be sure it came from the
#: OpenID domain.
AX_TYPE_CONTENT_ROLES = 'tag:nextthought.com,2011:ax/contentroles/1'

# The time limit for a GET request during
# the authentication process
_REQUEST_TIMEOUT = 0.5

def _authenticated_user( request ):
	"""
	Returns the User object authenticated by the request, or
	None if there is no user object authenticated by the request (which
	means either the credentials were invalid, or they are valid, but
	reference a user that no longer or doesn't exist; this can happen during
	testing when mixing site names up.)
	"""
	remote_user_name = sec.authenticated_userid( request )
	if remote_user_name:
		remote_user = users.User.get_user( remote_user_name )
		return remote_user

def _links_for_authenticated_users( request ):
	"""
	If a request is authenticated, returns links that should
	go to the user. Shared between ping and handshake.
	"""
	links = ()
	remote_user = _authenticated_user( request )
	if remote_user:
		logger.debug( "Found authenticated user %s", remote_user )
		# They are already logged in, provide a continue link
		continue_href = request.route_path( 'user.root.service', _='' )
		links = [ Link( continue_href, rel=REL_CONTINUE ) ]
		logout_href = request.route_path( REL_LOGIN_LOGOUT )
		links.append( Link( logout_href, rel=REL_LOGIN_LOGOUT ) )

		for provider in component.subscribers( (remote_user,request), app_interfaces.IAuthenticatedUserLinkProvider ):
			links.extend( provider.get_links() )

	return links

def _links_for_unauthenticated_users( request ):
	"""
	If a request is unauthenticated, returns links that should
	go to anonymous users.

	In particular, this will provide a link to be able to create accounts.
	"""
	links = ()
	remote_user = _authenticated_user( request )
	if not remote_user:

		create_account = request.route_path( 'objects.generic.traversal', traverse=('users') )

		create = Link( create_account, rel=REL_CREATE_ACCOUNT,
					   target_mime_type=mimetype.nti_mimetype_from_object( users.User ),
					   elements=('@@' + REL_CREATE_ACCOUNT,))
		preflight = Link( create_account, rel=REL_PREFLIGHT_CREATE_ACCOUNT,
						  target_mime_type=mimetype.nti_mimetype_from_object( users.User ),
						  elements=('@@' + REL_PREFLIGHT_CREATE_ACCOUNT,))

		forgot_username = Link( request.route_path( REL_FORGOT_USERNAME ),
								rel=REL_FORGOT_USERNAME )
		forgot_passcode = Link( request.route_path( REL_FORGOT_PASSCODE ),
								rel=REL_FORGOT_PASSCODE )
		reset_passcode = Link( request.route_path( REL_RESET_PASSCODE ),
							   rel=REL_RESET_PASSCODE )

		links = (create, preflight, forgot_username, forgot_passcode, reset_passcode)

	return links

def _forgetting( request, redirect_param_name, no_param_class, redirect_value=None, error=None ):
	"""
	:param redirect_param_name: The name of the request parameter we look for to provide
		a redirect URL.
	:param no_param_class: A factory to use to produce a response if no redirect
		has been specified. Commonly :class:`pyramid.httpexceptions.HTTPNoContent`
		or :class:`pyramid.httpexceptions.HTTPUnauthorized`.
	:type no_param_class: Callable of no arguments
	:keyword redirect_value: If given, this will be the redirect URL to use; `redirect_param_name`
		will be ignored.
	:keyword error: A string to add to the redirect URL as the ``error`` parameter.
	:return: The response object, set up for the redirect. The view (our caller) will return
		this.
	"""
	response = None
	if not redirect_value:
		redirect_value = request.params.get( redirect_param_name )

	if redirect_value:
		if error:
			parsed = urlparse.urlparse( redirect_value )
			parsed = list(parsed)
			query = parsed[4]
			if query:
				query = query + '&error=' + urllib.quote( error )
			else:
				query = 'error=' + urllib.quote( error )
			parsed[4] = query
			redirect_value = urlparse.urlunparse( parsed )

		response = hexc.HTTPSeeOther( location=redirect_value )
	else:
		response = no_param_class()
	# Clear any cookies they sent that failed.
	response.headers.extend( sec.forget(request) )
	if error:
		# TODO: Sending multiple warnings
		response.headers[b'Warning'] = error.encode('utf-8')

	logger.debug( "Forgetting user %s with %s (%s)", sec.authenticated_userid(request), response, response.headers )
	return response

@view_config(route_name=REL_LOGIN_LOGOUT, request_method='GET')
def logout(request):
	"Cause the response to the request to terminate the authentication."

	# Terminate any sessions they have open
	# TODO: We need to associate the socket.io session somehow
	# so we can terminate just that one session (we cannot terminate all,
	# multiple logins are allowed )
	return _forgetting( request, 'success', hexc.HTTPNoContent )

@view_config(route_name=REL_PING, request_method='GET', renderer='rest')
def ping( request ):
	"""
	The first step in authentication.

	:return: An externalizable object containing a link to the handshake URL, and potentially
		to the continue URL if authentication was provided and valid.
	"""
	links = []
	handshake_href = request.route_path( REL_HANDSHAKE )
	links.append( Link( handshake_href, rel=REL_HANDSHAKE ) )
	links.extend( _links_for_authenticated_users( request ) )
	links.extend( _links_for_unauthenticated_users( request ) )
	links.sort() # for tests
	return _Pong( links )

@interface.implementer( ext_interfaces.IExternalObject )
class _Pong(dict):

	__external_class_name__ = 'Pong'
	mime_type = mimetype.nti_mimetype_with_class( 'pong' )

	def __init__( self, lnks ):
		dict.__init__( self )
		self.links = lnks

@interface.implementer( app_interfaces.IMissingUser )
class NoSuchUser(object):

	def __init__( self, username ):
		self.username = username

	def has_password( self ):
		"We pretend to have a password so we can offer that login option."
		return True

@view_config(route_name=REL_HANDSHAKE, request_method='POST', renderer='rest')
def handshake(request):
	"""
	The second step in authentication. Inspects provided credentials
	to decide what sort of logins are possible.
	"""

	desired_username = request.params.get( 'username' )
	if not desired_username:
		return hexc.HTTPBadRequest(detail="Must provide username")

	# TODO: Check for existence in the database before generating these.
	# We also need to be validating whether we can do a openid login, etc.
	user = users.User.get_user( username=desired_username,
								dataserver=component.getUtility(nti_interfaces.IDataserver) )

	if user is None:
		# Use an IMissingUser so we find the right link providers
		user = NoSuchUser(desired_username)

	links = {}
	for provider in component.subscribers( (user,request), app_interfaces.ILogonLinkProvider ):
		if provider.rel in links:
			continue
		link = provider()
		if link is not None:
			links[link.rel] = link


	# Only allow one of login_google and login_openid. Both are
	# openid based, but login_openid is probably more specific than
	# the generic google so take that one (e.g., aops.com has both a custom
	# openid implementation and is also a google apps domain. Our discovery
	# process finds both, but we really just want the openid value).
	# This only happens in the case of a missing user (first login)
	if REL_LOGIN_OPENID in links and REL_LOGIN_GOOGLE in links:
		assert app_interfaces.IMissingUser.providedBy( user )
		del links[REL_LOGIN_GOOGLE]

	links = list( links.values() )

	links.extend( _links_for_authenticated_users( request ) )
	links.extend( _links_for_unauthenticated_users( request ) )
	links.sort()
	return _Handshake( links )

@interface.implementer( app_interfaces.ILogonLinkProvider )
@component.adapter( nti_interfaces.IUser, pyramid.interfaces.IRequest )
class _SimpleExistingUserLinkProvider(object):

	rel = REL_LOGIN_NTI_PASSWORD

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__(self):
		if self.user.has_password():
			return Link( self.request.route_path( self.rel, _query={'username': self.user.username}),
						 rel=self.rel )

@interface.implementer( app_interfaces.ILogonLinkProvider )
@component.adapter( app_interfaces.IMissingUser, pyramid.interfaces.IRequest )
class _SimpleMissingUserFacebookLinkProvider(object):

	rel = REL_LOGIN_FACEBOOK

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__(self):
		return Link( self.request.route_path( 'logon.facebook.oauth1', _query={'username': self.user.username} ),
					 rel=self.rel )

@component.adapter( nti_interfaces.IFacebookUser, pyramid.interfaces.IRequest )
class _SimpleExistingUserFacebookLinkProvider(_SimpleMissingUserFacebookLinkProvider):
	pass


def _prepare_oid_link( request, username, rel, params=() ):
	query = dict(params)
	query['oidcsum'] = _checksum(username) if 'oidcsum' not in query else query['oidcsum']
	query['username'] = username

	title = None
	if 'openid' in query:
		# We have to derive the title, we can't supply it from
		# the link provider because the link provider changes
		# when IMissingUser becomes a real user, and it's just one
		# for all open ids
		idurl_domain = urlparse.urlparse(query['openid']).netloc
		if idurl_domain:
			# Strip down to just the root domain. This assumes
			# we get a valid domain, at least 'example.com'
			idurl_domain = '.'.join( idurl_domain.split('.')[-2:] )
			title = _( 'Sign in with ${domain}',
					   mapping={'domain': idurl_domain} )
			title = translate( title, context=request ) # TODO: Make this automatic

	try:
		return Link( request.route_path( rel, _query=query ),
					 rel=rel,
					 title=title)
	except KeyError:
		# This is really a programmer/configuration error,
		# but we let it pass for tests
		logger.exception( "Unable to direct to route %s", rel )
		return

@interface.implementer( app_interfaces.ILogonLinkProvider )
@component.adapter( nti_interfaces.IUser, pyramid.interfaces.IRequest )
class _WhitelistedDomainGoogleLoginLinkProvider(object):
	"""
	Provides a Google login link for a predefined list of domains.
	"""
	rel = REL_LOGIN_GOOGLE

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	# TODO: We are never checking that the user we get actually comes
	# from one of these domains. Should we? Does it matter?
	domains = ('nextthought.com', 'gmail.com')
	def __call__( self ):
		if getattr( self.user, 'identity_url', None ) is not None:
			# They have a specific ID already, they don't need this
			return None

		domain = self.user.username.split( '@' )[-1]
		if domain in self.domains:
			return _prepare_oid_link( self.request, self.user.username, self.rel, params=self.params_for(self.user) )

	def params_for( self, user ):
		return ()

@component.adapter( app_interfaces.IMissingUser, pyramid.interfaces.IRequest )
class _MissingUserWhitelistedDomainGoogleLoginLinkProvider(_WhitelistedDomainGoogleLoginLinkProvider):
	"""
	Provides a Google login link for a predefined list of domains
	when an account needs to be created.
	"""

class _MissingUserAopsLoginLinkProvider(_MissingUserWhitelistedDomainGoogleLoginLinkProvider):
	"""
	Offer OpenID for accounts coming from aops.com. Once they successfully
	login they will just be normal OpenID users.
	"""

	# TODO: Should we use openid.aops.com? That way its consistent all the way
	# around
	domains = ('aops.com',)
	rel = REL_LOGIN_OPENID

	def params_for( self, user ):
		aops_username = self.user.username.split( '@' )[0]
		# Larry says:
		# > http://<username>.openid.artofproblemsolving.com
		# > http://openid.artofproblemsolving.com/<username>
		# > http://<username>.openid.aops.com
		# > http://openid.aops.com/<username>
		# But 3 definitely doesn't work. 1 and 4 do. We use 4
		return {'openid': 'http://openid.aops.com/%s' % aops_username }


	def getUsername( self, idurl, extra_info=None ):
		# reverse the process by tacking @aops.com back on
		username = idurl.split( '/' )[-1]
		username = username + '@' + self.domains[0]
		return username


class _MissingUserMallowstreetLoginLinkProvider(_MissingUserWhitelistedDomainGoogleLoginLinkProvider):
	"""
	Offer OpenID for accounts coming from mallowstreet.com (which themselves are probably already
	in the form of email addresses, so our incoming username may be 'first.last@example.com@mallowstreet.com').
	Following successful account creation they will just be normal OpenID users.
	"""

	domains = ('mallowstreet.com',)
	rel = REL_LOGIN_OPENID

	#: When we go to production, this will change to
	#: secure....
	_BASE_URL = 'https://demo.mallowstreet.com/Mallowstreet/OpenID/User.aspx/%s'

	def params_for( self, user ):
		# strip the trailing '@mallowstreet.com', preserving any previous
		# portion that looked like an email
		mallow_username = '@'.join(user.username.split('@')[0:-1])
		return {'openid': self._BASE_URL % mallow_username }


	def getUsername( self, idurl, extra_info=None ):
		# reverse the process by tacking @mallowstreet.com back on
		username = idurl.split( '/' )[-1]
		username = username + '@' + self.domains[0]
		return username

@interface.implementer( app_interfaces.ILogonLinkProvider )
@component.adapter( app_interfaces.IMissingUser, pyramid.interfaces.IRequest )
class _OnlineQueryGoogleLoginLinkProvider(object):
	"""
	Queries google to see if the domain is an Apps domain that
	we can expect to use google auth on.
	"""

	KNOWN_DOMAIN_CACHE = logilab.common.cache.Cache()

	rel = REL_LOGIN_GOOGLE

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__( self ):
		domain = self.user.username.split( '@' )[-1]
		allow = False
		cached = self.KNOWN_DOMAIN_CACHE.get( domain )
		if cached is not None:
			allow = cached
		else:
			try:
				google_rsp = requests.get( 'https://www.google.com/accounts/o8/.well-known/host-meta',
										   params={'hd': domain},
										   timeout=_REQUEST_TIMEOUT )
			except (IOError,RequestException):
				# Timeout or invalid network connection, no resolution, nothing to cache
				logger.info( "Timeout checking Google apps account for %s", domain )
				return None
			else:
				allow = google_rsp.status_code == 200
				self.KNOWN_DOMAIN_CACHE[domain] = allow

		if allow:
			return _prepare_oid_link( self.request, self.user.username, self.rel )

@component.adapter( nti_interfaces.IOpenIdUser, pyramid.interfaces.IRequest )
class _ExistingOpenIdUserLoginLinkProvider(object):

	rel = REL_LOGIN_OPENID

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def __call__( self ):
		return _prepare_oid_link( self.request, self.user.username, self.rel,
								  params={'openid': self.user.identity_url} )


@interface.implementer( ext_interfaces.IExternalObject )
class _Handshake(dict):

	__external_class_name__ = 'Handshake'
	mime_type = mimetype.nti_mimetype_with_class( 'handshake' )

	def __init__( self, lnks ):
		dict.__init__( self )
		self.links = lnks

def _create_failure_response( request, failure=None, error=None, error_factory=hexc.HTTPUnauthorized ):
	return _forgetting( request, 'failure', error_factory, redirect_value=failure, error=error )

def _create_success_response( request, userid=None, success=None ):
	"""
	Called when authentication was accepted. Returns a response
	that will remember the `userid` and optionally redirect
	to the `success` argument or request argument.

	:param userid: If given, the user id we will remember. If not given,
		then we will remember the currently authenticated user.
	:param success: If given, a path we will redirect to. If not given, then
		we will look for a HTTP param of the same name.
	"""
	redirect_to = success
	if redirect_to is None:
		redirect_to = request.params.get( 'success' )

	if redirect_to:
		response = hexc.HTTPSeeOther( location=redirect_to )
	else:
		response = hexc.HTTPNoContent()

	request.response = response # Make it the same to avoid confusing things that only get the request, e.g., event listeners

	userid = userid or sec.authenticated_userid( request )

	logon_userid_with_request( userid, request, response )

	return response

def _specified_username_logon( request, allow_no_username=True, require_matching_username=True, audit=False ):
	# This code handles both an existing logged on user and not
	remote_user = _authenticated_user( request )
	if not remote_user:
		return _create_failure_response( request ) # not authenticated or does not exist

	try:
		desired_usernames = request.params.getall( 'username' ) or []
	except AttributeError:
		# Nark. For test code. It's hard to always be able to use a real MultiDict
		desired_usernames = request.params.get( 'username', () )
		if desired_usernames:
			desired_usernames = [desired_usernames]

	if len(desired_usernames) > 1:
		return _create_failure_response( request, error_factory=hexc.HTTPBadRequest, error='Multiple usernames' )

	if desired_usernames:
		desired_username = desired_usernames[0].lower()
	elif allow_no_username:
		desired_username = remote_user.username.lower()
	else:
		return _create_failure_response( request, error_factory=hexc.HTTPBadRequest, error='No username' )


	if require_matching_username and desired_username != remote_user.username.lower():
		response = _create_failure_response( request ) # Usually a cookie/param mismatch
	else:
		try:
			response = _create_success_response( request, desired_username )
		except ValueError as e:
			return _create_failure_response( request, error_factory=hexc.HTTPNotFound, error=e.args[0]) # No such user

		if audit:
			# TODO: some real auditing scheme
			logger.info( "[AUDIT] User %s has impersonated %s at %s", remote_user, desired_username, request )
		response.cache_control.no_cache = True
	return response

@view_config(route_name=REL_LOGIN_NTI_PASSWORD, request_method='GET', renderer='rest')
def password_logon(request):
	"""
	Found at the path in :const:`REL_LOGIN_NTI_PASSWORD`, this takes authentication credentials
	(typically basic auth, but anything the app is configured to accept) and logs the user in
	or

	For extra assurance, the desired username may be sent as the request parameter `username`;
	if so, it must match the authenticated credentials. Any problems, including failure to authenticate,
	will result in an HTTP 40x response and may have a ``Warning`` header with
	additional details.

	The request parameter `success` can be used to indicate a redirection upon successful logon.
	Likewise, the parameter `failure` can be used for redirection on a failed attempt.
	"""
	# Note that this also accepts the authentication cookie, not just the Basic auth
	return _specified_username_logon( request )

@view_config(route_name=REL_LOGIN_IMPERSONATE,
			 request_method='GET',
			 permission=nauth.ACT_IMPERSONATE,
			 renderer='rest')
def impersonate_user(request):
	"""
	Users with the correct role for the site can get impersonation tickets
	for other users. (At this writing in Feb 2013, that means any @nextthought.com
	account can impersonate any user on any site.) The parameters and results
	are the same as for a normal logon (the authentication cookie is set, and the
	username cookie is set, both for the newly impersonated user).

	This should be easy to manually activate in the browser by visiting a URL such as
	``/dataserver2/logon.nti.impersonate?username=FOO&success=/``

	.. note :: This is currently a one-time thing. After you have impersonated, you will
		need to log out to log back in as your original account.

	See :func:`password_logon`.
	"""

	# TODO: auditing
	# TODO: This does the real logon steps for the impersonated user, including firing the events.
	# Is that what we want? We may want to do some things differently, such as causing some of the
	# profile links to not be sent back, thus bypassing the app's attempt to request new emails.
	# Need to think through this some more. Might be able to use the metadata providers in repoze.who,
	# or sessions to accomplish this.
	return _specified_username_logon( request, allow_no_username=False, require_matching_username=False, audit=True )

@interface.implementer( app_interfaces.IAuthenticatedUserLinkProvider )
@component.adapter( nti_interfaces.IUser, pyramid.interfaces.IRequest )
class ImpersonationLinkProvider(object):
	"""
	Add the impersonation link if available.
	"""
	rel = REL_LOGIN_IMPERSONATE

	def __init__( self, user, req ):
		self.request = req
		self.user = user

	def get_links( self ):
		if has_permission( nauth.ACT_IMPERSONATE, self.user, self.request ):
			return (Link( self.request.route_path( self.rel ),
						 rel=self.rel ),)
		return ()


import pyramid_openid.view

from zope.proxy import non_overridable
from zope.proxy.decorator import SpecificationDecoratorBase

# Pyramid_openid wants to read its settings from the global
# configuration at request.registry.settings. We may want to do things differently on different
# virtual sites or for different users. Thus, we proxy the path to
# request.registry.settings.

class _PyramidOpenidRegistryProxy(SpecificationDecoratorBase):

	def __init__( self, base ):
		SpecificationDecoratorBase.__init__( self, base )
		self._settings = dict(base.settings)

	@non_overridable
	@property
	def settings(self):
		return self._settings

class _PyramidOpenidRequestProxy(SpecificationDecoratorBase):

	def __init__( self, base ):
		SpecificationDecoratorBase.__init__( self, base )
		self.registry = _PyramidOpenidRegistryProxy( base.registry )

_OPENID_FIELD_NAME = 'openid2'
def _openid_configure( request ):
	"""
	Configure the settings needed for pyramid_openid on this request.
	"""
	# Here, we set up the sreg and ax values

	settings = { 'openid.param_field_name': _OPENID_FIELD_NAME,
				 'openid.success_callback': 'nti.appserver.logon:_openidcallback',
				# Google uses a weird mix of namespaces. It only supports these values, plus
				# country (http://code.google.com/apis/accounts/docs/OpenID.html#endpoint)
				 'openid.ax_required': 'email=http://schema.openid.net/contact/email firstname=http://axschema.org/namePerson/first lastname=http://axschema.org/namePerson/last',
				 'openid.ax_optional': 'content_roles=' + AX_TYPE_CONTENT_ROLES,
				 # See _openidcallback: Sreg isn't used anywhere right now, so it's disabled
				 # Note that there is an sreg value for 'nickname' that could serve as
				 # our 'alias' if we wanted to try to ask for it.
				 #'openid.sreg_required': 'email fullname nickname language'
				 }
	request.registry.settings.update( settings )

from openid.extensions import ax
# ensure the patch is needed and going to apply correctly
assert pyramid_openid.view.ax is ax
assert 'AttrInfo' not in pyramid_openid.view.__dict__

class _AttrInfo(ax.AttrInfo):
	"""
	Pyramid_openid provides no way to specify the 'count' value, but we
	need to set it to unlimited for :const:`AX_TYPE_CONTENT_ROLES` (because the default
	is one and the provider is not supposed to return more than that). So we subclass
	and monkey patch to change the value. (Subclassing ensures that isinstance checks continue
	to work)
	"""

	def __init__( self, type_uri, **kwargs ):
		if type_uri == AX_TYPE_CONTENT_ROLES:
			kwargs['count'] = ax.UNLIMITED_VALUES
		super(_AttrInfo,self).__init__( type_uri, **kwargs )

ax.AttrInfo = _AttrInfo

def _openid_login(context, request, openid='https://www.google.com/accounts/o8/id', params=None):
	"""
	Wrapper around :func:`pyramid_openid.view.verify_openid` that takes care of some error handling
	and settings.
	"""
	if params is None:
		params = request.params
	if 'oidcsum' not in params:
		logger.warn( "oidcsum not present in %s at %s", params, request )
		return _create_failure_response( request, error="Invalid params; missing oidcsum" )


	openid_field = _OPENID_FIELD_NAME
	# pyramid_openid routes back to whatever URL we initially came from;
	# we always want it to be from our response wrapper
	nrequest = pyramid.request.Request.blank( request.route_url( ROUTE_OPENID_RESPONSE, _query=params ),
											  # In theory, if we're constructing the URL correctly, this is enough
											  # to carry through HTTPS info
											  base_url=request.host_url,
											  POST={openid_field: openid } )
	nrequest.registry = request.registry
	nrequest = _PyramidOpenidRequestProxy( nrequest )
	assert request.registry is not nrequest.registry
	assert request.registry.settings is not nrequest.registry.settings
	_openid_configure( nrequest )
	logger.debug( "Directing pyramid request to %s", nrequest )

	# If the discover process fails, the view will do two things:
	# (1) Flash a message in the session queue request.settings.get('openid.error_flash_queue', '')
	# (2) redirect to request.settings.get( 'openid.errordestination', '/' )
	# We have a better way to return errors, and we want to use it,
	# so we scan for the error_flash.
	# NOTE: We are assuming that neither of these is configured, and that
	# nothing else uses the flash queue
	q_name = request.registry.settings.get( 'openid.error_flash_queue', '' )
	q_b4 = nrequest.session.pop_flash( q_name )
	assert len(q_b4) == 0

	result = pyramid_openid.view.verify_openid( context, nrequest )

	q_after = nrequest.session.pop_flash(q_name)
	if result is None:
		# This is a programming/configuration error in 0.3.4, meaning we have
		# failed to pass required params. For example, the openid_param_name might not match
		raise AssertionError( "Failure to get response object; check configs" )
	elif q_after != q_b4:
		# Error
		result = _create_failure_response( request, error=q_after[0] )
	return result

@view_config(route_name=ROUTE_OPENID_RESPONSE)#, request_method='GET')
def _openid_response(context, request):
	"""
	Process an OpenID response. This exists as a wrapper around
	:func:`pyramid_openid.view.verify_openid` because that function
	does nothing on failure, but we need to know about failure. (This is as-of
	0.3.4; it is fixed in trunk.)
	"""
	response = None
	openid_mode = request.params.get( 'openid.mode', None )
	if openid_mode != 'id_res':
		# Failure.
		response = _create_failure_response( request )
	else:
		# If we call directly, we miss the ax settings
		#response = pyramid_openid.view.verify_openid( context, request )
		response = _openid_login( context, request )
	return response


@view_config(route_name=REL_LOGIN_GOOGLE, request_method="GET")
def google_login(context, request):
	return _openid_login( context, request )

@view_config(route_name=REL_LOGIN_OPENID, request_method="GET")
def openid_login(context, request):
	if 'openid' not in request.params:
		return _create_failure_response( request, error='Missing openid' )
	return _openid_login( context, request, request.params['openid'] )


def _deal_with_external_account( request, username, fname, lname, email, idurl, iface, user_factory ):
	"""
	Finds or creates an account based on an external authentication.

	:param username: The login name the user typed. Must be globally unique, and
		should be in the form of an email.
	:param email: The email the user provides. Should be an email. Not required.
	:param idul: The URL that identifies the user on the external system.
	:param iface: The interface that the user object will implement.
	:return: The user object
	"""

	dataserver = component.getUtility(nti_interfaces.IDataserver)
	user = users.User.get_user( username=username, dataserver=dataserver )
	url_attr = iface.names()[0]
	if user:
		if not iface.providedBy( user ):
			interface.alsoProvides( user, iface )
			setattr( user, url_attr, idurl )
			lifecycleevent.modified( user, lifecycleevent.Attributes( iface, url_attr ) )
		assert getattr( user, url_attr ) == idurl
	else:
		# When creating, we go through the same steps as account_creation_views,
		# guaranteeing the proper validation
		external_value = { 'Username': username,
						   'realname': fname + ' ' + lname,
						   url_attr: idurl,
						   'email': email }
		from .account_creation_views import _create_user # XXX A bit scuzzy

		# This fires lifecycleevent.IObjectCreatedEvent and IObjectAddedEvent. The oldParent attribute
		# will be None
		user = _create_user( request, external_value, require_password=False, user_factory=user_factory )
		__traceback_info__ = request, user_factory, iface, user
		assert getattr( user, url_attr ) is None # doesn't get read from the external value right now
		setattr( user, url_attr, idurl )
		assert getattr( user, url_attr ) == idurl
		assert iface.providedBy( user )
		# We manually fire the user_created event. See account_creation_views
		notify( app_interfaces.UserCreatedWithRequestEvent( user, request ) )
	return user

def _update_users_content_roles( user, idurl, content_roles ):
	"""
	Update the content roles assigned to the given user based on information
	returned from an external provider.

	:param user: The user object
	:param idurl: The URL identifying the user on the external system. All
		content roles we update will be based on this idurl; in particular, we assume
		that the base hostname of the URL maps to a NTIID ``provider``, and we will
		only add/remove roles from this provider. For example, ``http://openid.primia.org/username``
		becomes the provider ``prmia.``
	:param iterable content_roles: An iterable of strings naming provider-local
		content roles. If empty/None, then the user will be granted no roles
		from the provider of the ``idurl``; otherwise, the content roles from the given
		``provider`` will be updated to match. The local roles can be the exact (case-insensitive) match
		for the title of a work, and the user will be granted access to the derived NTIID for the work
		whose title matches. Otherwise (no title match), the user will be granted direct access
		to the role as given.
	"""
	member = component.getAdapter( user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX )
	if not content_roles and not member.hasGroups():
		return # No-op

	provider = urlparse.urlparse( idurl ).netloc.split( '.' )[-2] # http://x.y.z.nextthought.com/openid => nextthought
	provider = provider.lower()

	empty_role = nauth.role_for_providers_content( provider, '' )

	# Delete all of our provider's roles, leaving everything else intact
	other_provider_roles = [x for x in member.groups if not x.id.startswith( empty_role.id )]
	# Create new roles for what they tell us
	# NOTE: At this step here we may need to map from external provider identifiers (stock numbers or whatever)
	# to internal NTIID values. Somehow. Searching titles is one way to ease that

	library = component.queryUtility( lib_interfaces.IContentPackageLibrary )

	roles_to_add = []
	# Set up a map from title to list-of specific-parts-of-ntiids for all content from this provider
	provider_packages = {}
	for package in (library.contentPackages if library is not None else ()):
		if ntiids.get_provider( package.ntiid ).lower() == provider:
			provider_packages.setdefault( package.title.lower(), [] ).append( ntiids.get_specific( package.ntiid ) )

	for local_role in (content_roles or ()):
		local_role = local_role.lower()
		if local_role in provider_packages:
			for specific in provider_packages[local_role]:
				roles_to_add.append( nauth.role_for_providers_content( provider, specific ) )
		else:
			roles_to_add.append( nauth.role_for_providers_content( provider, local_role ) )


	member.setGroups( other_provider_roles + roles_to_add )

from zlib import crc32
def _checksum( username ):
	return str(crc32(username)) # must be stable across machines

def _openidcallback( context, request, success_dict ):
	# It seems that the identity_url is actually
	# ignored by google and we get back identifying information for
	# whatever user is currently signed in. This can have strange consequences
	# with mismatched URLs and emails (you are signed in, but not as who you
	# indicated you wanted to be signed in as): It's not a security problems because
	# we use the credentials you actually authenticated with, its just confusing.
	# To try to prevent this, we are using a basic checksum approach to see if things
	# match: oidcsum. In some cases we can't do that, though
	idurl = success_dict['identity_url']
	oidcsum = request.params.get( 'oidcsum' )

	# Google only supports AX, sreg is ignored.
	# AoPS gives us back nothing, ignoring both AX and sreg.
	# So right now, even though we ask for both, we are also totally ignoring
	# sreg

	# In AX, there can be 0 or more values; the openid library always represents
	# this using a list (see openid.extensions.ax.AXKeyValueMessage.get and pyramid_openid.view.process_provider_response)
	ax_dict = success_dict.get( 'ax', {} )
	fname = ax_dict.get('firstname', ('',))[0]
	lname = ax_dict.get('lastname', ('',))[0]
	email = ax_dict.get('email', ('',))[0]
	content_roles = ax_dict.get( 'content_roles', () )

	idurl_domain = urlparse.urlparse( idurl ).netloc
	username_provider = component.queryMultiAdapter( (None,request), app_interfaces.ILogonUsernameFromIdentityURLProvider, name=idurl_domain )
	if username_provider:
		username = username_provider.getUsername( idurl, success_dict )
	elif email:
		username = email
	else:
		return _create_failure_response(request, error='Unable to derive username')


	if _checksum(username) != oidcsum:
		   logger.warn( "Checksum mismatch. Logged in multiple times? %s %s username=%s prov=%s", oidcsum, success_dict, username, username_provider)
		   return _create_failure_response(request, error='Username/Email checksum mismatch')

	try:
		# TODO: Make this look the interface and factory to assign up by name (something in the idurl?)
		# That way we can automatically assign an IAoPSUser and use a users.AoPSUser
		the_user = _deal_with_external_account( request, username, fname, lname, email, idurl, nti_interfaces.IOpenIdUser, users.OpenIdUser.create_user )
		_update_users_content_roles( the_user, idurl, content_roles )
	except hexc.HTTPError:
		raise
	except Exception as e:
		return _create_failure_response( request, error=str(e) )


	return _create_success_response( request, userid=the_user.username )


@component.adapter(nti_interfaces.IUser,app_interfaces.IUserLogonEvent)
def _user_did_logon( user, event ):
	user.update_last_login_time()


###
# TODO: The two facebook methods below could be radically simplified using
# requests-facebook. As of 0.1.1, it adds no dependencies. (However, it also has no tests in its repo)
# http://pypi.python.org/pypi/requests-facebook/0.1.1
###

@view_config( route_name='logon.facebook.oauth1', request_method='GET' )
def facebook_oauth1( request ):
	app_id = request.registry.settings.get( 'facebook.app.id' )
	our_uri = urllib.quote( request.route_url( 'logon.facebook.oauth2' ) )
	# We seem incapable of sending any parameters with the redirect_uri. If we do,
	# then the validation step 400's. Thus we resort to the session
	for k in ('success','failure'):
		if request.params.get( k ):
			request.session['facebook.' + k] = request.params.get( k )

	request.session['facebook.username'] = request.params.get('username')
	redir_to = 'https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&scope=email' % (app_id, our_uri)

	return hexc.HTTPSeeOther( location=redir_to )

@view_config( route_name='logon.facebook.oauth2', request_method='GET' )
def facebook_oauth2(request):

	if 'error' in request.params:
		return _create_failure_response( request, request.session.get('facebook.failure'), error=request.params.get('error') )

	code = request.params['code']
	app_id = request.registry.settings.get( 'facebook.app.id' )
	our_uri = request.route_url( 'logon.facebook.oauth2' )
	app_secret = request.registry.settings.get( 'facebook.app.secret' )

	auth = requests.get( 'https://graph.facebook.com/oauth/access_token',
						 params={'client_id': app_id, 'redirect_uri': our_uri, 'client_secret': app_secret, 'code': code},
						 timeout=_REQUEST_TIMEOUT )

	try:
		auth.raise_for_status()
	except RequestException as req_ex:
		logger.exception( "Failed facebook login %s", auth.text )
		return _create_failure_response(request, request.session.get('facebook.failure'), error=str(req_ex))


	# The facebook return value is in ridiculous format.
	# Are we supposed to try to treat this like a url query value or
	# something? Yick.
	# TODO: try urlparse.parse_qsl. We need test cases!
	text = auth.text
	token = None
	for x in text.split( '&'):
		if x.startswith('access_token='):
			token = x[len('access_token='):]
			break

	data = requests.get( 'https://graph.facebook.com/me',
						 params={'access_token': token},
						 timeout=_REQUEST_TIMEOUT )
	data = json.loads( data.text )
	if data['email'] != request.session.get('facebook.username'):
		logger.warn( "Facebook username returned different emails %s != %s", data['email'], request.session.get('facebook.username') )
		return _create_failure_response( request, request.session.get('facebook.failure'), error='Facebook resolved to different username' )

	user = _deal_with_external_account( request, data['email'], # TODO: Assuming email address == username
										data['first_name'], data['last_name'],
										data['email'], data['link'],
										nti_interfaces.IFacebookUser,
										users.FacebookUser.create_user )


	# For the data formats, see here:
	# https://developers.facebook.com/docs/reference/api/user/
	# Fire off requests for the user's data that we want, plus
	# the address of his picture.
	pic_rsp = requests.get( 'https://graph.facebook.com/me/picture',
							params={'access_token': token},
							allow_redirects=False, # This should return a 302, we want the location, not the data
							timeout=_REQUEST_TIMEOUT,
							return_response=False )
							# TODO: Used to support 'config={safe_mode':True}' to "catch all errors"
							#config={'safe_mode': True} )
	# Do we have a facebook picture to use? If so, snag it and use it.
	# TODO: Error handling. TODO: We could do this more async.
	if pic_rsp.status_code == 302:
		pic_location = pic_rsp.headers['Location']
		if pic_location and pic_location != user.avatarURL:
			user.avatarURL = pic_location

	return _create_success_response( request, userid=data['email'], success=request.session.get('facebook.success') )
