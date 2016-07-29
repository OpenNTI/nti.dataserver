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


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger(__name__)

import urllib
import urlparse
import collections
import anyjson as json

# Clean up the logging of openid, which writes to stderr by default.
# Patching the module like this is actually the recommended approach
from openid import oidutil
oidutil.log = logging.getLogger('openid').info

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.event import notify

from zope.i18n import translate

from zope.traversing import api as ztraversing

import pyramid.request
import pyramid.interfaces
import pyramid.httpexceptions as hexc

from pyramid import security as sec

from pyramid.view import view_config

import requests
from requests.exceptions import RequestException

from nti.app.renderers.interfaces import IResponseCacheController
from nti.app.renderers.interfaces import IPrivateUncacheableInResponse

from nti.appserver import MessageFactory as _

from nti.appserver._util import logon_userid_with_request

from nti.appserver.account_recovery_views import REL_RESET_PASSCODE
from nti.appserver.account_creation_views import REL_CREATE_ACCOUNT
from nti.appserver.account_recovery_views import REL_FORGOT_PASSCODE
from nti.appserver.account_recovery_views import REL_FORGOT_USERNAME
from nti.appserver.account_creation_views import REL_PREFLIGHT_CREATE_ACCOUNT

from nti.appserver.interfaces import ILogonPong
from nti.appserver.interfaces import IMissingUser
from nti.appserver.interfaces import IUserLogonEvent
from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IAuthenticatedUserLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider
from nti.appserver.interfaces import ILogonUsernameFromIdentityURLProvider

from nti.appserver.interfaces import UserLogoutEvent
from nti.appserver.interfaces import UserCreatedWithRequestEvent

from nti.appserver.link_providers import flag_link_provider
from nti.appserver.link_providers import unique_link_providers

from nti.appserver.pyramid_authorization import has_permission

from nti.contentlibrary import interfaces as lib_interfaces

from nti.common.string import is_true

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.interfaces import IGoogleUser

from nti.dataserver.users import User
from nti.dataserver.users import OpenIdUser
from nti.dataserver.users import FacebookUser

from nti.dataserver.users.interfaces import GoogleUserCreatedEvent

from nti.dataserver.users.utils import force_email_verification

from nti.externalization.interfaces import IExternalObject

from nti.links.links import Link

from nti.mimetype import mimetype

from nti.ntiids import ntiids

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

TOS_URL = 'https://docs.google.com/document/pub?id=1rM40we-bbPNvq8xivEKhkoLE7wmIETmO4kerCYmtISM&amp;embedded=true'
PRIVACY_POLICY_URL = 'https://docs.google.com/document/pub?id=1W9R8s1jIHWTp38gvacXOStsfmUz5TjyDYYy3CVJ2SmM'

# Link providing the direct link to the
# Terms-of-service page in its href
REL_TOS_URL = 'content.direct_tos_link'
REL_PRIVACY_POLICY_URL = 'content.direct_privacy_link'

REL_PING = 'logon.ping'  # See :func:`ping`
REL_HANDSHAKE = 'logon.handshake'  # : See :func:`handshake`
REL_CONTINUE = 'logon.continue'

REL_LOGIN_LOGOUT = 'logon.logout'  # See :func:`logout`
REL_LOGIN_NTI_PASSWORD = 'logon.nti.password'  # See :func:`password_logon`
REL_LOGIN_IMPERSONATE = 'logon.nti.impersonate'  # See :func:`impersonate_user`

REL_LOGIN_GOOGLE = 'logon.google'
REL_LOGIN_OPENID = 'logon.openid'  # See :func:`openid_login`
REL_LOGIN_FACEBOOK = 'logon.facebook'  # See :func:`facebook_oauth1`

ROUTE_OPENID_RESPONSE = 'logon.openid.response'

# The URI used as in attribute exchange to request the content to which
# the authenticated entity has access. The attribute value type is defined
# as a list of unlimited length, each entry of which refers to a specific
# :class:`nti.contentlibrary.interfaces.IContentPackage`. Certain providers
# may have special mapping rules, but in general, each entry is the specific local
# part of the NTIID of that content package (and the provider is implied from the
# OpenID domain). These will be turned into groups that the :class:`nti.dataserver.interfaces.IUser`
# is a member of; see :class:`nti.dataserver.interfaces.IGroupMember` and :mod:`nti.dataserver.authorization_acl`.
#
# The NTIID of each content package thus referenced should be checked to be sure it came from the
# OpenID domain.
AX_TYPE_CONTENT_ROLES = 'tag:nextthought.com,2011:ax/contentroles/1'

#: The time limit for a GET request during
#: the authentication process
_REQUEST_TIMEOUT = 0.5

def _authenticated_user(request):
	"""
	Returns the User object authenticated by the request, or
	None if there is no user object authenticated by the request (which
	means either the credentials were invalid, or they are valid, but
	reference a user that no longer or doesn't exist; this can happen during
	testing when mixing site names up.)
	"""
	remote_user_name = request.authenticated_userid
	if remote_user_name:
		remote_user = User.get_user(remote_user_name)
		return remote_user

def _links_for_authenticated_users(request):
	"""
	If a request is authenticated, returns links that should
	go to the user. Shared between ping and handshake.
	"""
	links = ()
	remote_user = _authenticated_user(request)
	if remote_user:
		logger.debug("Found authenticated user %s", remote_user)

		# They are already logged in, provide a continue link
		continue_href = request.route_path('user.root.service', _='')
		links = [ Link(continue_href, rel=REL_CONTINUE, elements=('service',)) ]

		logout_href = request.route_path(REL_LOGIN_LOGOUT)
		links.append(Link(logout_href, rel=REL_LOGIN_LOGOUT))

		for _, prov_links in unique_link_providers(remote_user, request, True):
			links.extend(prov_links)

	links = tuple(links) if links else ()
	return links

def _links_for_unauthenticated_users(request):
	"""
	If a request is unauthenticated, returns links that should
	go to anonymous users.

	In particular, this will provide a link to be able to create accounts.
	"""
	links = ()
	remote_user = _authenticated_user(request)
	if not remote_user:

		forgot_username = Link(request.route_path(REL_FORGOT_USERNAME),
							   rel=REL_FORGOT_USERNAME)

		forgot_passcode = Link(request.route_path(REL_FORGOT_PASSCODE),
							   rel=REL_FORGOT_PASSCODE)

		reset_passcode = Link(request.route_path(REL_RESET_PASSCODE),
							  rel=REL_RESET_PASSCODE)

		links = [forgot_username, forgot_passcode, reset_passcode]

		# These may be security controlled
		root = component.getUtility(nti_interfaces.IDataserver).root_folder
		for rel in REL_CREATE_ACCOUNT, REL_PREFLIGHT_CREATE_ACCOUNT:
			route = request.route_path('objects.generic.traversal', traverse=(rel,))
			resource = ztraversing.traverse(root, route, request=request)
			try:
				yes = has_permission(nauth.ACT_CREATE, resource, request)
			except ValueError:  # Test cases that don't have a complete policy setup
				yes = False

			if yes:
				links.append(Link(route, rel=rel,
								  target_mime_type=mimetype.nti_mimetype_from_object(User)))


		for provider in component.subscribers((request,), IUnauthenticatedUserLinkProvider):
			links.extend(provider.get_links())

	links = tuple(links) if links else ()
	return links

def _forgetting(request, redirect_param_name, no_param_class, redirect_value=None, error=None):
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
		redirect_value = request.params.get(redirect_param_name)

	if redirect_value:
		if error:
			parsed = urlparse.urlparse(redirect_value)
			parsed = list(parsed)
			query = parsed[4]
			if query:
				query = query + '&error=' + urllib.quote(error)
			else:
				query = 'error=' + urllib.quote(error)
			parsed[4] = query
			redirect_value = urlparse.urlunparse(parsed)

		response = hexc.HTTPSeeOther(location=redirect_value)
	else:
		response = no_param_class()
	# Clear any cookies they sent that failed.
	response.headers.extend(sec.forget(request))
	if error:
		# TODO: Sending multiple warnings
		response.headers[b'Warning'] = error.encode('utf-8')

	logger.debug("Forgetting user %s with %s (%s)",
				 request.authenticated_userid,
				 response,
				 response.headers)
	return response

@view_config(route_name=REL_LOGIN_LOGOUT, request_method='GET')
def logout(request):
	"Cause the response to the request to terminate the authentication."

	# Terminate any sessions they have open
	# TODO: We need to associate the socket.io session somehow
	# so we can terminate just that one session (we cannot terminate all,
	# multiple logins are allowed )
	response = _forgetting(request, 'success', hexc.HTTPNoContent)
	username = request.authenticated_userid
	user = User.get_user(username)
	notify(UserLogoutEvent(user, request))
	return response

@view_config(route_name=REL_PING, request_method='GET', renderer='rest')
def ping(request):
	"""
	The first step in authentication.

	:return: An externalizable object containing a link to the handshake URL, and potentially
		to the continue URL if authentication was provided and valid.
	"""
	links = []
	handshake_href = request.route_path(REL_HANDSHAKE)
	links.append(Link(handshake_href, rel=REL_HANDSHAKE))
	links.extend(_links_for_authenticated_users(request))
	links.extend(_links_for_unauthenticated_users(request))
	links.sort()  # for tests

	username = request.authenticated_userid
	result = _Pong(links)
	if username:
		result['AuthenticatedUsername'] = username
	return result

@interface.implementer(ILogonPong,
					   IExternalObject,
					   IPrivateUncacheableInResponse)
class _Pong(dict):

	__external_class_name__ = 'Pong'
	mime_type = mimetype.nti_mimetype_with_class('pong')

	def __init__(self, lnks):
		dict.__init__(self)
		self.links = lnks

@interface.implementer(IMissingUser)
class NoSuchUser(object):

	def __init__(self, username):
		self.username = username

	def has_password(self):
		"We pretend to have a password so we can offer that login option."
		return True

@view_config(route_name=REL_HANDSHAKE, request_method='POST', renderer='rest')
def handshake(request):
	"""
	The second step in authentication. Inspects provided credentials
	to decide what sort of logins are possible.
	"""
	desired_username = request.params.get('username')
	if not desired_username:
		return hexc.HTTPBadRequest(detail="Must provide username")

	# TODO: Check for existence in the database before generating these.
	# We also need to be validating whether we can do a openid login, etc.
	user = User.get_user(username=desired_username,
						 dataserver=component.getUtility(nti_interfaces.IDataserver))

	if user is None:
		# Use an IMissingUser so we find the right link providers
		user = NoSuchUser(desired_username)

	links = {}
	# First collect the providers, then sort them, putting them in
	# priority order by link type, basically. This is because the order of subscribers
	# is non-deterministic when multiple registries are involved.
	# If any provider raises the NotImplementedError when called, that link
	# type will be dropped if it hasn't been seen yet.
	providers = []
	for provider in component.subscribers((user, request), ILogonLinkProvider):
		providers.append((provider.rel, getattr(provider, 'priority', 0), provider))

	ignored = set()
	for rel, _, provider in sorted(providers, reverse=True):
		if rel in links or rel in ignored:
			continue

		try:
			link = provider()
		except NotImplementedError:
			ignored.add(rel)
		else:
			if link is not None:
				links[link.rel] = link

	links = list(links.values())
	links.extend(_links_for_authenticated_users(request))
	links.extend(_links_for_unauthenticated_users(request))
	links.sort()

	username = request.authenticated_userid
	result = _Handshake(links)
	if username:
		result['AuthenticatedUsername'] = username
	return result

@interface.implementer(ILogonLinkProvider)
@component.adapter(nti_interfaces.IUser, pyramid.interfaces.IRequest)
class _SimpleExistingUserLinkProvider(object):

	rel = REL_LOGIN_NTI_PASSWORD

	def __init__(self, user, req):
		self.request = req
		self.user = user

	def __call__(self):
		if self.user.has_password():
			return Link(self.request.route_path(self.rel, _query={'username': self.user.username}),
						rel=self.rel)


@interface.implementer(IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.IUser, pyramid.interfaces.IRequest)
class _OnlinePolicyLinkProvider (object):

	tos_rel = REL_TOS_URL
	privacy_rel = REL_PRIVACY_POLICY_URL

	def __init__ (self, user, req):
		self.request = req
		self.user = user

	def get_links (self):
		return (Link (target=TOS_URL, rel=self.tos_rel),
				Link (target=PRIVACY_POLICY_URL, rel=self.privacy_rel),)

@interface.implementer(ILogonLinkProvider)
@component.adapter(IMissingUser, pyramid.interfaces.IRequest)
class _SimpleMissingUserFacebookLinkProvider(object):

	rel = REL_LOGIN_FACEBOOK

	def __init__(self, user, req):
		self.request = req
		self.user = user

	def __call__(self):
		return Link(self.request.route_path('logon.facebook.oauth1', _query={'username': self.user.username}),
					rel=self.rel)

@component.adapter(nti_interfaces.IFacebookUser, pyramid.interfaces.IRequest)
class _SimpleExistingUserFacebookLinkProvider(_SimpleMissingUserFacebookLinkProvider):
	pass

def _prepare_oid_link(request, username, rel, params=()):
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
			idurl_domain = '.'.join(idurl_domain.split('.')[-2:])
			title = _('Sign in with ${domain}',
					   mapping={'domain': idurl_domain})
			title = translate(title, context=request)  # TODO: Make this automatic

	try:
		return Link(request.route_path(rel, _query=query),
					rel=rel,
					title=title)
	except KeyError:
		# This is really a programmer/configuration error,
		# but we let it pass for tests
		logger.exception("Unable to direct to route %s", rel)
		return

@interface.implementer(ILogonLinkProvider)
@component.adapter(nti_interfaces.IUser, pyramid.interfaces.IRequest)
class WhitelistedDomainLinkProviderMixin(object):
	"""
	Provides a login link for a predefined list of domains.
	"""
	rel = None

	def __init__(self, user, req):
		self.user = user
		self.request = req

	# TODO: We are never checking that the user we get actually comes
	# from one of these domains. Should we? Does it matter?
	domains = ('nextthought.com', 'gmail.com')

	def __call__(self):
		if getattr(self.user, 'identity_url', None) is not None:
			# They have a specific ID already, they don't need this
			return None

		domain = self.user.username.split('@')[-1]
		if domain in self.domains:
			return _prepare_oid_link(self.request,
									 self.user.username,
									 self.rel,
									 params=self.params_for(self.user))

	def params_for(self, user):
		return ()

@component.adapter(IMissingUser, pyramid.interfaces.IRequest)
class MissingUserWhitelistedLinkProviderMixin(WhitelistedDomainLinkProviderMixin):
	"""
	Provides a Google login link for a predefined list of domains
	when an account needs to be created.
	"""

class _MissingUserAopsLoginLinkProvider(MissingUserWhitelistedLinkProviderMixin):
	"""
	Offer OpenID for accounts coming from aops.com. Once they successfully
	login they will just be normal OpenID users.
	"""

	# TODO: Should we use openid.aops.com? That way its consistent all the way
	# around
	domains = ('aops.com',)
	rel = REL_LOGIN_OPENID

	def params_for(self, user):
		aops_username = self.user.username.split('@')[0]
		# Larry says:
		# > http://<username>.openid.artofproblemsolving.com
		# > http://openid.artofproblemsolving.com/<username>
		# > http://<username>.openid.aops.com
		# > http://openid.aops.com/<username>
		# But 3 definitely doesn't work. 1 and 4 do. We use 4
		return {'openid': 'http://openid.aops.com/%s' % aops_username }

	def getUsername(self, idurl, extra_info=None):
		# reverse the process by tacking @aops.com back on
		username = idurl.split('/')[-1]
		username = username + '@' + self.domains[0]
		return username

class _MissingUserMallowstreetLoginLinkProvider(MissingUserWhitelistedLinkProviderMixin):
	"""
	Offer OpenID for accounts coming from mallowstreet.com (which themselves are probably already
	in the form of email addresses, so our incoming username may be 'first.last@example.com@mallowstreet.com').
	Following successful account creation they will just be normal OpenID users.
	"""

	domains = ('mallowstreet.com',)
	rel = REL_LOGIN_OPENID

	# : When we go to production, this will change to
	# : secure....
	_BASE_URL = 'https://demo.mallowstreet.com/Mallowstreet/OpenID/User.aspx/%s'

	def params_for(self, user):
		# strip the trailing '@mallowstreet.com', preserving any previous
		# portion that looked like an email
		mallow_username = '@'.join(user.username.split('@')[0:-1])
		return {'openid': self._BASE_URL % mallow_username }

	def getUsername(self, idurl, extra_info=None):
		# reverse the process by tacking @mallowstreet.com back on
		username = idurl.split('/')[-1]
		username = username + '@' + self.domains[0]
		return username

@component.adapter(nti_interfaces.IOpenIdUser, pyramid.interfaces.IRequest)
class _ExistingOpenIdUserLoginLinkProvider(object):

	rel = REL_LOGIN_OPENID

	def __init__(self, user, req):
		self.request = req
		self.user = user

	def __call__(self):
		return _prepare_oid_link(self.request, self.user.username, self.rel,
								 params={'openid': self.user.identity_url})

@interface.implementer(IExternalObject,
					   IPrivateUncacheableInResponse)
class _Handshake(dict):

	__external_class_name__ = 'Handshake'
	mime_type = mimetype.nti_mimetype_with_class('handshake')

	def __init__(self, lnks):
		dict.__init__(self)
		self.links = lnks

def _create_failure_response(request, failure=None, error=None, error_factory=hexc.HTTPUnauthorized):
	return _forgetting(request, 'failure', error_factory, redirect_value=failure, error=error)

def _create_success_response(request, userid=None, success=None):
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
		redirect_to = request.params.get('success')

	if redirect_to:
		response = hexc.HTTPSeeOther(location=redirect_to)
	else:
		response = hexc.HTTPNoContent()

	request.response = response  # Make it the same to avoid confusing things that only get the request, e.g., event listeners

	userid = userid or request.authenticated_userid

	logon_userid_with_request(userid, request, response)

	return response

def _specified_username_logon(request, allow_no_username=True, require_matching_username=True, audit=False):
	# This code handles both an existing logged on user and not
	remote_user = _authenticated_user(request)
	if not remote_user:
		return _create_failure_response(request)  # not authenticated or does not exist

	try:
		desired_usernames = request.params.getall('username') or []
	except AttributeError:
		# Nark. For test code. It's hard to always be able to use a real MultiDict
		desired_usernames = request.params.get('username', ())
		if desired_usernames:
			desired_usernames = [desired_usernames]

	if len(desired_usernames) > 1:
		return _create_failure_response(request, error_factory=hexc.HTTPBadRequest, error=_('Multiple usernames'))

	if desired_usernames:
		desired_username = desired_usernames[0].lower()
	elif allow_no_username:
		desired_username = remote_user.username.lower()
	else:
		return _create_failure_response(request, error_factory=hexc.HTTPBadRequest, error=_('No username'))

	if require_matching_username and desired_username != remote_user.username.lower():
		response = _create_failure_response(request)  # Usually a cookie/param mismatch
	else:
		try:
			# If we're impersonating, record that fact in the cookie.
			# This will later show up in the environment and error/feedback
			# reports. This is a pretty basic version of that; if we use
			# it for anything more than display, we need to formalize it more.
			if desired_username != remote_user.username.lower():
				request.environ['REMOTE_USER_DATA'] = str(remote_user.username.lower())
			response = _create_success_response(request, desired_username)
		except ValueError as e:
			return _create_failure_response(request,
											error_factory=hexc.HTTPNotFound,
											error=e.args[0])  # No such user

		if audit:
			# TODO: some real auditing scheme
			logger.info("[AUDIT] User %s has impersonated %s at %s",
						remote_user, desired_username, request)

	# Mark this response up as if it were entirely private and not to be cached
	private_data = _Handshake(())
	IResponseCacheController(private_data)(private_data, {'request': request})

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
	return _specified_username_logon(request)

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
	return _specified_username_logon(request,
									 allow_no_username=False,
									 require_matching_username=False,
									 audit=True)

@interface.implementer(IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.IUser, pyramid.interfaces.IRequest)
class ImpersonationLinkProvider(object):
	"""
	Add the impersonation link if available.
	"""
	rel = REL_LOGIN_IMPERSONATE

	def __init__(self, user, req):
		self.request = req
		self.user = user

	def get_links(self):
		# check on the parent of the user, because users typically get
		# the AllPermission on themselves
		if has_permission(nauth.ACT_IMPERSONATE, self.user.__parent__, self.request):
			return (Link(self.request.route_path(self.rel),
						 rel=self.rel),)
		return ()

import pyramid_openid.view

from zope.proxy import non_overridable
from zope.proxy.decorator import SpecificationDecoratorBase

# Pyramid_openid wants to read its settings from the global
# configuration at request.registry.settings. We may want to do things differently on different
# virtual sites or for different users. Thus, we proxy the path to
# request.registry.settings.

class _PyramidOpenidRegistryProxy(SpecificationDecoratorBase):

	def __init__(self, base):
		SpecificationDecoratorBase.__init__(self, base)
		self._settings = dict(base.settings)

	@non_overridable
	@property
	def settings(self):
		return self._settings

class _PyramidOpenidRequestProxy(SpecificationDecoratorBase):

	def __init__(self, base):
		SpecificationDecoratorBase.__init__(self, base)
		self.registry = _PyramidOpenidRegistryProxy(base.registry)

_OPENID_FIELD_NAME = 'openid2'
def _openid_configure(request):
	"""
	Configure the settings needed for pyramid_openid on this request.
	"""
	# Here, we set up the sreg and ax values

	settings = { 'openid.param_field_name': _OPENID_FIELD_NAME,
				 'openid.success_callback': 'nti.appserver.logon:_openidcallback',
				 # Previously, google used a weird mix of namespaces, requiring openid.net
				 # for email. Now it seems to accept axschema for everything. See:
				 # https://developers.google.com/accounts/docs/OpenID#endpoint
				 'openid.ax_required': 'email=http://axschema.org/contact/email firstname=http://axschema.org/namePerson/first lastname=http://axschema.org/namePerson/last',
				 'openid.ax_optional': 'content_roles=' + AX_TYPE_CONTENT_ROLES,
				 # See _openidcallback: Sreg isn't used anywhere right now, so it's disabled
				 # Note that there is an sreg value for 'nickname' that could serve as
				 # our 'alias' if we wanted to try to ask for it.
				 # 'openid.sreg_required': 'email fullname nickname language'
	}
	request.registry.settings.update(settings)

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

	def __init__(self, type_uri, **kwargs):
		if type_uri == AX_TYPE_CONTENT_ROLES:
			kwargs['count'] = ax.UNLIMITED_VALUES
		super(_AttrInfo, self).__init__(type_uri, **kwargs)

ax.AttrInfo = _AttrInfo

def _openid_login(context, request, openid=None, params=None):
	"""
	Wrapper around :func:`pyramid_openid.view.verify_openid` that takes care of some error handling
	and settings.
	"""
	if params is None:
		params = request.params
	if 'oidcsum' not in params:
		logger.warn("oidcsum not present in %s at %s", params, request)
		return _create_failure_response(request, error="Invalid params; missing oidcsum")
	if openid is None:
		openid = params.get('openid.identity', params.get('openid')) or 'https://www.google.com/accounts/o8/id'

	openid_field = _OPENID_FIELD_NAME
	# pyramid_openid routes back to whatever URL we initially came from;
	# we always want it to be from our response wrapper
	nenviron = request.environ.copy()
	nenviron.pop('PATH_INFO', '')
	nenviron.pop('RAW_URI', '')
	nenviron.pop('webob._parsed_post_vars', '')
	nenviron.pop('webob._parsed_query_vars', '')
	post = {openid_field: openid}
	if request.POST:
		# Some providers ask the browser to do a form submission
		# via POST instead of having all params in the query string,
		# so we must support both
		post = request.POST.copy()
		post[openid_field] = openid

	if request.params.get('openid.mode') == 'id_res':
		# If the openid is provided, it takes precedence over openid.mode,
		# potentially leading to an infinite loop
		del post[openid_field]

	nrequest = pyramid.request.Request.blank(request.route_url(ROUTE_OPENID_RESPONSE, _query=params),
											 environ=nenviron,
											 # In theory, if we're constructing the URL correctly, this is enough
											 # to carry through HTTPS info
											 base_url=request.host_url,
											 headers=request.headers,
											 POST=post)
	nrequest.registry = request.registry
	nrequest.possible_site_names = getattr(request, 'possible_site_names', ())
	nrequest = _PyramidOpenidRequestProxy(nrequest)
	assert request.registry is not nrequest.registry
	assert request.registry.settings is not nrequest.registry.settings
	_openid_configure(nrequest)
	logger.debug("Directing pyramid request to %s", nrequest)

	# If the discover process fails, the view will do two things:
	# (1) Flash a message in the session queue request.settings.get('openid.error_flash_queue', '')
	# (2) redirect to request.settings.get( 'openid.errordestination', '/' )
	# We have a better way to return errors, and we want to use it,
	# so we scan for the error_flash.
	# NOTE: We are assuming that neither of these is configured, and that
	# nothing else uses the flash queue
	q_name = request.registry.settings.get('openid.error_flash_queue', '')
	q_b4 = nrequest.session.pop_flash(q_name)
	assert len(q_b4) == 0

	result = pyramid_openid.view.verify_openid(context, nrequest)

	q_after = nrequest.session.pop_flash(q_name)
	if result is None:
		# This is a programming/configuration error in 0.3.4, meaning we have
		# failed to pass required params. For example, the openid_param_name might not match
		raise AssertionError("Failure to get response object; check configs")
	elif q_after != q_b4:
		# Error
		result = _create_failure_response(request, error=q_after[0])
	return result

@view_config(route_name=ROUTE_OPENID_RESPONSE)  # , request_method='GET')
def _openid_response(context, request):
	"""
	Process an OpenID response. This exists as a wrapper around
	:func:`pyramid_openid.view.verify_openid` because that function
	does nothing on failure, but we need to know about failure. (This is as-of
	0.3.4; it is fixed in trunk.)
	"""
	response = None
	openid_mode = request.params.get('openid.mode', None)
	if openid_mode != 'id_res':
		# Failure.
		error = None
		if openid_mode == 'error':
			error = request.params.get('openid.error', None)
		if not error:
			if openid_mode == 'cancel':  # Hmm. Take a guess
				error = _("The request was canceled by the remote server.")
		response = _create_failure_response(request, error=error)
	else:
		# If we call directly, we miss the ax settings
		# response = pyramid_openid.view.verify_openid( context, request )
		response = _openid_login(context, request)
	return response

@view_config(route_name=REL_LOGIN_OPENID, request_method="GET")
def openid_login(context, request):
	if 'openid' not in request.params:
		return _create_failure_response(request, error='Missing openid')
	return _openid_login(context, request, request.params['openid'])

def _deal_with_external_account(request, username, fname, lname, email, idurl, iface, user_factory):
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
	user = User.get_user(username=username, dataserver=dataserver)
	url_attr = iface.names()[0] if iface and iface.names() and idurl else None
	if user:
		if iface and not iface.providedBy(user):
			interface.alsoProvides(user, iface)
			if url_attr:
				setattr(user, url_attr, idurl)
				lifecycleevent.modified(user, lifecycleevent.Attributes(iface, url_attr))
		if url_attr:
			assert getattr(user, url_attr) == idurl
	else:
		# When creating, we go through the same steps as account_creation_views,
		# guaranteeing the proper validation
		external_value = { 'Username': username, 'email':email }
		if fname and lname:
			external_value['realname'] = fname + ' ' + lname
		if url_attr:
			external_value[url_attr] = idurl

		require_password = False
		from .account_creation_views import _create_user  # XXX A bit scuzzy

		# This fires lifecycleevent.IObjectCreatedEvent and IObjectAddedEvent. The oldParent attribute
		# will be None
		user = _create_user(request, external_value, require_password=require_password, user_factory=user_factory)
		__traceback_info__ = request, user_factory, iface, user

		if url_attr:
			assert getattr(user, url_attr) is None  # doesn't get read from the external value right now
			setattr(user, url_attr, idurl)
			assert getattr(user, url_attr) == idurl
		if iface:
			assert iface.providedBy(user)
		# We manually fire the user_created event. See account_creation_views
		notify(UserCreatedWithRequestEvent(user, request))
	return user

def _update_users_content_roles(user, idurl, content_roles):
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
	member = component.getAdapter(user, nti_interfaces.IMutableGroupMember, nauth.CONTENT_ROLE_PREFIX)
	if not content_roles and not member.hasGroups():
		return  # No-op

	provider = urlparse.urlparse(idurl).netloc.split('.')[-2]  # http://x.y.z.nextthought.com/openid => nextthought
	provider = provider.lower()

	empty_role = nauth.role_for_providers_content(provider, '')

	# Delete all of our provider's roles, leaving everything else intact
	other_provider_roles = [x for x in member.groups if not x.id.startswith(empty_role.id)]
	# Create new roles for what they tell us
	# NOTE: At this step here we may need to map from external provider identifiers (stock numbers or whatever)
	# to internal NTIID values. Somehow. Searching titles is one way to ease that

	library = component.queryUtility(lib_interfaces.IContentPackageLibrary)

	roles_to_add = []
	# Set up a map from title to list-of specific-parts-of-ntiids for all content from this provider
	provider_packages = collections.defaultdict(list)
	for package in (library.contentPackages if library is not None else ()):
		if ntiids.get_provider(package.ntiid).lower() == provider:
			provider_packages[package.title.lower()].append(ntiids.get_specific(package.ntiid))

	for local_role in (content_roles or ()):
		local_role = local_role.lower()
		if local_role in provider_packages:
			for specific in provider_packages[local_role]:
				roles_to_add.append(nauth.role_for_providers_content(provider, specific))
		else:
			roles_to_add.append(nauth.role_for_providers_content(provider, local_role))

	member.setGroups(other_provider_roles + roles_to_add)

from zlib import crc32
def _checksum(username):
	return str(crc32(username))  # must be stable across machines

def _openidcallback(context, request, success_dict):
	# It seems that the identity_url is actually
	# ignored by google and we get back identifying information for
	# whatever user is currently signed in. This can have strange consequences
	# with mismatched URLs and emails (you are signed in, but not as who you
	# indicated you wanted to be signed in as): It's not a security problems because
	# we use the credentials you actually authenticated with, its just confusing.
	# To try to prevent this, we are using a basic checksum approach to see if things
	# match: oidcsum. In some cases we can't do that, though
	idurl = success_dict['identity_url']
	oidcsum = request.params.get('oidcsum')

	# Google only supports AX, sreg is ignored.
	# AoPS gives us back nothing, ignoring both AX and sreg.
	# So right now, even though we ask for both, we are also totally ignoring
	# sreg

	# In AX, there can be 0 or more values; the openid library always represents
	# this using a list (see openid.extensions.ax.AXKeyValueMessage.get and pyramid_openid.view.process_provider_response)
	ax_dict = success_dict.get('ax', {})
	fname = ax_dict.get('firstname', ('',))[0]
	lname = ax_dict.get('lastname', ('',))[0]
	email = ax_dict.get('email', ('',))[0]
	content_roles = ax_dict.get('content_roles', ())

	idurl_domain = urlparse.urlparse(idurl).netloc
	username_provider = component.queryMultiAdapter((None, request),
													ILogonUsernameFromIdentityURLProvider,
													name=idurl_domain)
	if username_provider:
		username = username_provider.getUsername(idurl, success_dict)
	elif email:
		username = email
	else:
		return _create_failure_response(request, error='Unable to derive username')


	if _checksum(username) != oidcsum:
		logger.warn("Checksum mismatch. Logged in multiple times? %s %s username=%s prov=%s",
					oidcsum, success_dict, username, username_provider)
		return _create_failure_response(request, error='Username/Email checksum mismatch')

	try:
		# TODO: Make this look the interface and factory to assign up by name (something in the idurl?)
		# That way we can automatically assign an IAoPSUser and use a users.AoPSUser
		the_user = _deal_with_external_account(request, username=username, fname=fname, lname=lname, email=email,
											   idurl=idurl, iface=nti_interfaces.IOpenIdUser,
											   user_factory=OpenIdUser.create_user)
		_update_users_content_roles(the_user, idurl, content_roles)
	except hexc.HTTPError:
		raise
	except Exception as e:
		return _create_failure_response(request, error=str(e))


	return _create_success_response(request, userid=the_user.username)

@component.adapter(nti_interfaces.IUser, IUserLogonEvent)
def _user_did_logon(user, event):
	request = event.request
	request.environ[b'nti.request_had_transaction_side_effects'] = b'True'
	if not user.lastLoginTime:
		# First time logon, notify the client
		flag_link_provider.add_link(user, 'first_time_logon')
	user.update_last_login_time()

# TODO: The two facebook methods below could be radically simplified using
# requests-facebook. As of 0.1.1, it adds no dependencies.
# (However, it also has no tests in its repo)
# http://pypi.python.org/pypi/requests-facebook/0.1.1

FB_DIAG_OAUTH = 'https://www.facebook.com/dialog/oauth'

@view_config(route_name='logon.facebook.oauth1', request_method='GET')
def facebook_oauth1(request):
	app_id = request.registry.settings.get('facebook.app.id')
	our_uri = urllib.quote(request.route_url('logon.facebook.oauth2'))
	# We seem incapable of sending any parameters with the redirect_uri. If we do,
	# then the validation step 400's. Thus we resort to the session
	for k in ('success', 'failure'):
		if request.params.get(k):
			request.session['facebook.' + k] = request.params.get(k)

	request.session['facebook.username'] = request.params.get('username')
	redir_to = '%s?client_id=%s&redirect_uri=%s&scope=email' % (FB_DIAG_OAUTH, app_id, our_uri)
	return hexc.HTTPSeeOther(location=redir_to)

@view_config(route_name='logon.facebook.oauth2', request_method='GET')
def facebook_oauth2(request):

	if 'error' in request.params:
		return _create_failure_response(request,
										request.session.get('facebook.failure'),
										error=request.params.get('error'))

	code = request.params['code']
	app_id = request.registry.settings.get('facebook.app.id')
	our_uri = request.route_url('logon.facebook.oauth2')
	app_secret = request.registry.settings.get('facebook.app.secret')

	auth = requests.get('https://graph.facebook.com/oauth/access_token',
						params={'client_id': app_id,
								'redirect_uri': our_uri,
								'client_secret': app_secret,
								'code': code},
						timeout=_REQUEST_TIMEOUT)

	try:
		auth.raise_for_status()
	except RequestException as req_ex:
		logger.exception("Failed facebook login %s", auth.text)
		return _create_failure_response(request,
										request.session.get('facebook.failure'),
										error=str(req_ex))

	# The facebook return value is in ridiculous format.
	# Are we supposed to try to treat this like a url query value or
	# something? Yick.
	# TODO: try urlparse.parse_qsl. We need test cases!
	text = auth.text
	token = None
	for x in text.split('&'):
		if x.startswith('access_token='):
			token = x[len('access_token='):]
			break

	data = requests.get('https://graph.facebook.com/me',
						 params={'access_token': token},
						 timeout=_REQUEST_TIMEOUT)
	data = json.loads(data.text)
	if data['email'] != request.session.get('facebook.username'):
		logger.warn("Facebook username returned different emails %s != %s",
					data['email'], request.session.get('facebook.username'))
		return _create_failure_response(request,
										request.session.get('facebook.failure'),
										error='Facebook resolved to different username')

	# TODO: Assuming email address == username
	user = _deal_with_external_account(request, username=data['email'],
									   fname=data['first_name'], lname=data['last_name'],
									   email=data['email'], idurl=data['link'],
									   iface=nti_interfaces.IFacebookUser,
									   user_factory=FacebookUser.create_user)

	# For the data formats, see here:
	# https://developers.facebook.com/docs/reference/api/user/
	# Fire off requests for the user's data that we want, plus
	# the address of his picture.
	pic_rsp = requests.get('https://graph.facebook.com/me/picture',
							params={'access_token': token},
							allow_redirects=False,  # This should return a 302, we want the location, not the data
							timeout=_REQUEST_TIMEOUT,
							return_response=False)
							# TODO: Used to support 'config={safe_mode':True}' to "catch all errors"
							# config={'safe_mode': True} )
	# Do we have a facebook picture to use? If so, snag it and use it.
	# TODO: Error handling. TODO: We could do this more async.
	if pic_rsp.status_code == 302:
		pic_location = pic_rsp.headers['Location']
		if pic_location and pic_location != user.avatarURL:
			user.avatarURL = pic_location

	result = _create_success_response(request,
									  userid=data['email'],
									  success=request.session.get('facebook.success'))
	return result

# google

import os
import hashlib
from urlparse import urljoin

from nti.appserver.interfaces import IGoogleLogonSettings

from nti.utils.interfaces import IOAuthKeys

OPENID_CONFIGURATION = None
LOGON_GOOGLE_OAUTH2 = 'logon.google.oauth2'
DEFAULT_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
DEFAULT_TOKEN_URL = 'https://www.googleapis.com/oauth2/v4/token'
DEFAULT_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
DISCOVERY_DOC_URL = 'https://accounts.google.com/.well-known/openid-configuration'

def _redirect_uri(request):
	root = request.route_path('objects.generic.traversal', traverse=())
	root = root[:-1] if root.endswith('/') else root
	target = urljoin(request.application_url, root)
	target = target + '/' if not target.endswith('/') else target
	target = urljoin(target, LOGON_GOOGLE_OAUTH2)
	return target

def get_openid_configuration():
	global OPENID_CONFIGURATION
	if not OPENID_CONFIGURATION:
		s = requests.get(DISCOVERY_DOC_URL)
		OPENID_CONFIGURATION = s.json() if s.status_code == 200 else {}
	return OPENID_CONFIGURATION

@view_config(route_name=REL_LOGIN_GOOGLE, request_method='GET')
def google_oauth1(request):
	auth_keys = component.getUtility(IOAuthKeys, name="google")
	state = hashlib.sha256(os.urandom(1024)).hexdigest()
	config = get_openid_configuration()
	auth_url = config.get("authorization_endpoint", DEFAULT_AUTH_URL)
	params = {'state': state,
			  'scope': 'openid email profile',
			  'response_type': 'code',
			  'client_id':auth_keys.APIKey,
			  'redirect_uri':_redirect_uri(request)}

	hosted_domain = None
	login_config = component.queryUtility(IGoogleLogonSettings)
	if login_config is not None:
		hosted_domain = login_config.hd
	if hosted_domain:
		params['hd'] = hosted_domain

	for k in ('success', 'failure'):
		if request.params.get(k):
			request.session['google.' + k] = request.params.get(k)

	# save state for validation
	request.session['google.state'] = state

	# redirect
	target = auth_url[:-1] if auth_url.endswith('/') else auth_url
	target = '%s?%s' % (target, urllib.urlencode(params))
	response = hexc.HTTPSeeOther(location=target)
	return response

@view_config(route_name=LOGON_GOOGLE_OAUTH2, request_method='GET')
def google_oauth2(request):
	params = request.params
	auth_keys = component.getUtility(IOAuthKeys, name="google")

	# check for errors
	if 'error' in params or 'errorCode' in params:
		error = params.get('error') or params.get('errorCode')
		return _create_failure_response(request,
										request.session.get('google.failure'),
										error=error)

	# Confirm code
	if 'code' not in params:
		return _create_failure_response(request,
										request.session.get('google.failure'),
										error=_('Could not find code parameter.'))
	code = params.get('code')

	# Confirm anti-forgery state token
	if 'state' not in params:
		return _create_failure_response(request,
										request.session.get('google.failure'),
										error=_('Could not find state parameter.'))
	params_state = params.get('state')
	session_state = request.session.get('google.state')
	if params_state != session_state:
		return _create_failure_response(request,
										request.session.get('google.failure'),
										error=_('Incorrect state values.'))

	# Exchange code for access token and ID token
	config = get_openid_configuration()
	token_url = config.get('token_endpoint', DEFAULT_TOKEN_URL)

	try:
		data = {'code':code,
				'client_id':auth_keys.APIKey,
				'grant_type':'authorization_code',
				'client_secret':auth_keys.SecretKey,
				'redirect_uri':_redirect_uri(request)}
		response = requests.post(token_url, data)
		if response.status_code != 200:
			return _create_failure_response(
								request,
								request.session.get('google.failure'),
								error=_('Invalid response while getting access token.'))

		data = response.json()
		if 'access_token' not in data:
			return _create_failure_response(request,
											request.session.get('google.failure'),
											error=_('Could not find access token.'))
		if 'id_token' not in data:
			return _create_failure_response(request,
											request.session.get('google.failure'),
											error=_('Could not find id token.'))

		# id_token = data['id_token'] #TODO:Validate id token
		access_token = data['access_token']
		logger.debug("Getting user profile")
		userinfo_url = config.get('userinfo_endpoint', DEFAULT_USERINFO_URL)
		response = requests.get(userinfo_url, params={"access_token":access_token})
		if response.status_code != 200:
			return _create_failure_response(request,
											request.session.get('google.failure'),
											error=_('Invalid access token.'))
		profile = response.json()
		username = profile['email']
		user = User.get_entity(username)
		if user is None:
			firstName = profile.get('given_name', 'unspecified')
			lastName = profile.get('family_name', 'unspecified')
			email_verified = profile.get('email_verified', 'false')

			user = _deal_with_external_account(request,
											   username=username,
											   fname=firstName,
											   lname=lastName,
											   email=username,
											   idurl=None,
											   iface=None,
											   user_factory=User.create_user)
			interface.alsoProvides(user, IGoogleUser)
			notify(GoogleUserCreatedEvent(user))
			if is_true(email_verified):
				force_email_verification(user)  # trusted source
			request.environ[b'nti.request_had_transaction_side_effects'] = b'True'

		response = _create_success_response(request,
											userid=username,
											success=request.session.get('google.success'))
	except Exception as e:
		logger.exception('Failed to login with google')
		response = _create_failure_response(request,
											request.session.get('google.failure'),
											error=str(e))
	return response
