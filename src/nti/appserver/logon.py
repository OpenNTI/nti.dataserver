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

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import hashlib
import logging

from six.moves import urllib_parse

import simplejson as json

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

from pyramid.interfaces import IRequest

from pyramid.view import view_config

import requests
from requests.exceptions import RequestException

from nti.app.renderers.interfaces import IResponseCacheController
from nti.app.renderers.interfaces import IPrivateUncacheableInResponse

from nti.app.users.utils import get_user_creation_sitename

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
from nti.appserver.interfaces import IImpersonationDecider
from nti.appserver.interfaces import IAuthenticatedUserLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider
from nti.appserver.interfaces import ILogoutForgettingResponseProvider
from nti.appserver.interfaces import ILogonUsernameFromIdentityURLProvider

from nti.appserver.interfaces import UserLogoutEvent
from nti.appserver.interfaces import UserCreatedWithRequestEvent

from nti.appserver.link_providers import flag_link_provider
from nti.appserver.link_providers import unique_link_providers

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.appserver.pyramid_authorization import has_permission

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.users.interfaces import OpenIDUserCreatedEvent

from nti.dataserver.users.users import User
from nti.dataserver.users.users import OpenIdUser
from nti.dataserver.users.users import FacebookUser

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IExternalObject
from nti.externalization.interfaces import StandardExternalFields

from nti.links.links import Link

from nti.mimetype import mimetype

from nti.securitypolicy.utils import is_impersonating

logger = logging.getLogger(__name__)

HREF = StandardExternalFields.HREF
CLASS = StandardExternalFields.CLASS
MIMETYPE = StandardExternalFields.MIMETYPE
LINKS = StandardExternalFields.LINKS

#: Link relationship indicating a welcome page
#: Fetching the href of this link returns either a content page
#: or PageInfo structure. The client is expected to DELETE
#: this link once the user has viewed it.
REL_INITIAL_WELCOME_PAGE = u"content.initial_welcome_page"

#: Link relationship indicating a welcome page
#: The client is expected to make this relationship
#: available to the end user at all times. It is NOT a deletable
#: link.
REL_PERMANENT_WELCOME_PAGE = u'content.permanent_welcome_page'

#: Link relationship indicating the Terms-of-service page
#: Fetching the href of this link returns either a content page
#: or PageInfo structure. The client is expected to DELETE
#: this link once the user has viewed it and accepted it.
REL_INITIAL_TOS_PAGE = u"content.initial_tos_page"

#: Link relationship indicating a the Terms-of-service page
#: The client is expected to make this relationship
#: available to the end user at all times for review. It is NOT a deletable
#: link.
REL_PERMANENT_TOS_PAGE = u'content.permanent_tos_page'

REL_PING = 'logon.ping'  # See :func:`ping`
REL_HANDSHAKE = 'logon.handshake'  #: See :func:`handshake`
REL_CONTINUE = 'logon.continue'
REL_CONTINUE_ANONYMOUSLY = 'logon.continue-anonymously'

REL_LOGIN_LOGOUT = 'logon.logout'  # See :func:`logout`
REL_LOGIN_NTI_PASSWORD = 'logon.nti.password'  # See :func:`password_logon`
REL_LOGIN_IMPERSONATE = 'logon.nti.impersonate'  # See :func:`impersonate_user`

REL_LOGIN = 'logon.nti'  # See :func:`general_logon`

REL_LOGIN_OPENID = 'logon.openid'  # See :func:`openid_login`
REL_LOGIN_FACEBOOK = 'logon.facebook'  # See :func:`facebook_oauth1`

ROUTE_OPENID_RESPONSE = 'logon.openid.response'

# The URI used as in attribute exchange to request the content to which
# the authenticated entity has access. The attribute value type is defined
# as a list of unlimited length, each entry of which refers to a specific
#:class:`nti.contentlibrary.interfaces.IContentPackage`. Certain providers
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

#: The link relationship type that
#: indicates we know that the email recorded for this user is bad and
#: has received permanent bounces. The user must be asked to enter a
#: new one and update the profile. Send an HTTP DELETE to this link
#: when you are done updating the profile to remove the flag.
REL_INVALID_EMAIL = 'state-bounced-email'

#: The link relationship type that
#: indicates that a contact email (aka parent email) recorded for
#: this (under 13) user has received permanent bounces. The child
#: must be asked to enter a new contact_email and update the profile.
#: When the profile is updated, a new consent email will be
#: generated. Send an HTTP DELETE to this link with you are done
#: updating the profile to remove the flag.
REL_INVALID_CONTACT_EMAIL = 'state-bounced-contact-email'


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
        links = [Link(continue_href, rel=REL_CONTINUE, elements=('service',))]

        logout_href = request.route_path(REL_LOGIN_LOGOUT)
        links.append(Link(logout_href, rel=REL_LOGIN_LOGOUT))

        for _, prov_links in unique_link_providers(remote_user, request, True):
            links.extend(prov_links)

    # For impersonating, do not show welcome page and TOS page, invalid emails dialogs.
    if links and (is_impersonating(request) or (remote_user and remote_user.username.endswith('@nextthought.com'))):
        links = [x for x in links if x.rel not in (REL_INITIAL_WELCOME_PAGE,
                                                   REL_INITIAL_TOS_PAGE,
                                                   REL_INVALID_EMAIL,
                                                   REL_INVALID_CONTACT_EMAIL)]
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
            route = request.route_path('objects.generic.traversal',
                                       traverse=(rel,))
            resource = ztraversing.traverse(root, route, request=request)
            try:
                yes = has_permission(nauth.ACT_CREATE, resource, request)
            except ValueError:  # Test cases that don't have a complete policy setup
                yes = False

            if yes:
                links.append(Link(route, rel=rel,
                                  target_mime_type=mimetype.nti_mimetype_from_object(User)))

        for _, prov_links in unique_link_providers(None, request, True):
            links.extend(prov_links)

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
            parsed = urllib_parse.urlparse(redirect_value)
            parsed = list(parsed)
            query = parsed[4]
            if query:
                query = query + '&error=' + urllib_parse.quote(error)
            else:
                query = 'error=' + urllib_parse.quote(error)
            parsed[4] = query
            redirect_value = urllib_parse.urlunparse(parsed)

        response = hexc.HTTPSeeOther(location=redirect_value)
    else:
        response = no_param_class()
    # Clear any cookies they sent that failed.
    response.headers.extend(sec.forget(request))
    if error:
        # TODO: Sending multiple warnings
        response.headers['Warning'] = error.encode('utf-8')

    logger.debug("Forgetting user %s with %s (%s)",
                 request.authenticated_userid,
                 response,
                 response.headers)
    return response


@component.adapter(IRequest)
@interface.implementer(IUnauthenticatedUserLinkProvider)
class ContinueAnonymouslyLinkProvider(object):

    def __init__(self, request):
        self.request = request

    def get_links(self):
        continue_href = self.request.route_path('user.root.service', _='')
        return (Link(continue_href,
                     rel=REL_CONTINUE_ANONYMOUSLY,
                     elements=('service',)), )


@interface.implementer(ILogoutForgettingResponseProvider)
class DefaultLogoutResponseProvider(object):

    def __init__(self, request):
        pass

    def forgetting(self, request, redirect_param_name, redirect_value=None):
        return _forgetting(request, redirect_param_name,
                           hexc.HTTPNoContent, redirect_value=redirect_value)


@view_config(route_name=REL_LOGIN_LOGOUT, request_method='GET')
def logout(request):
    """
    Cause the response to the request to terminate the authentication.
    """
    # Terminate any sessions they have open
    # TODO: We need to associate the socket.io session somehow
    # so we can terminate just that one session (we cannot terminate all,
    # multiple logins are allowed )
    logout_response_provider = ILogoutForgettingResponseProvider(request)
    response = logout_response_provider.forgetting(request, 'success')
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
    policy = component.getUtility(ISitePolicyUserEventListener)
    support_email = getattr(policy, 'SUPPORT_EMAIL', 'support@nextthought.com')
    links.append({CLASS: 'Link',
                  HREF: u'mailto:%s' % support_email,
                  'rel': 'support-email',
                  'title': u'Email'})
    links.sort()  # for tests

    username = request.authenticated_userid
    result = _Pong(links)
    if username:
        result.AuthenticatedUsername = username

        # As of 12/4/2019 we are only using this for google analytics.
        # We want something unique and stable that ids the user but that isn't
        # PII and isn't easy to reverse. We use a one way hash of an identifier
        # based off the username and user creation site if it exists.
        #
        # TODO: Really we add the site because users are only specific to a db.
        # We collect analytics across all environements and we don't want collisions.
        # The current site isn't exactly right especially in a child site scenario like
        # ifsta. It also probably isn't accurate if people jump between vanity urls.
        # so we use the user creation site. This still isn't guarenteed to be unique, but
        # in practice, in our current and known future setups it will be

        scope = get_user_creation_sitename(username)
        uid = username + u'@' + scope if scope else username
        result.AuthenticatedUserId = hashlib.md5(uid).hexdigest()
    return result


@interface.implementer(ILogonPong,
                       IExternalObject,
                       IPrivateUncacheableInResponse)
class _Pong(dict):

    __external_class_name__ = 'Pong'

    mime_type = mimetype.nti_mimetype_with_class('pong')

    AuthenticatedUsername = None
    AuthenticatedUserId = None

    def __init__(self, lnks):
        dict.__init__(self)
        self.links = lnks

    def toExternalObject(self, **kwargs):
        return InterfaceObjectIO(self, ILogonPong).toExternalObject(**kwargs)


@interface.implementer(IMissingUser)
class NoSuchUser(object):

    def __init__(self, username):
        self.username = username

    def has_password(self):
        """
        We pretend to have a password so we can offer that login option.
        """
        return True


@view_config(route_name=REL_HANDSHAKE, request_method='POST', renderer='rest')
def handshake(request):
    """
    The second step in authentication. Inspects provided credentials
    to decide what sort of logins are possible.
    """
    desired_username = request.params.get('username', '')

    # TODO: Check for existence in the database before generating these.
    # We also need to be validating whether we can do a openid login, etc.
    user = None
    if desired_username:
        user = User.get_user(username=desired_username,
                             dataserver=component.getUtility(nti_interfaces.IDataserver))

    if user is None:
        # Use an IMissingUser so we find the right link providers.
        # Now that we allow no username to be provided we could opt,
        # in that case, for a INoUser object rather than an IMissingUser
        # with no username.  This would, for example, give us an
        # easy way to not send back the logon.nti.password provider if
        # we wanted.
        user = NoSuchUser(desired_username)

    links = {}
    # First collect the providers, then sort them, putting them in
    # priority order by link type, basically. This is because the order of subscribers
    # is non-deterministic when multiple registries are involved.
    # If any provider raises the NotImplementedError when called, that link
    # type will be dropped if it hasn't been seen yet.
    providers = []
    for provider in component.subscribers((user, request), ILogonLinkProvider):
        providers.append((provider.rel,
                          getattr(provider, 'priority', 0),
                          provider))

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
            path = self.request.route_path(self.rel,
                                           _query={'username': self.user.username})
            return Link(path, rel=self.rel)


@interface.implementer(IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.IUser, pyramid.interfaces.IRequest)
class DoNotAdvertiseWelcomePageLinksProvider(object):
    """
    This link provider should be registered as subscriber in sites
    where they don't want to show the welcome page.
    """

    priority = 1
    rels = (REL_INITIAL_WELCOME_PAGE, REL_PERMANENT_WELCOME_PAGE)

    def __init__(self, *args, **kwargs):
        pass

    def get_links(self):
        raise NotImplementedError()


@interface.implementer(ILogonLinkProvider)
@component.adapter(IMissingUser, pyramid.interfaces.IRequest)
class _SimpleMissingUserFacebookLinkProvider(object):

    rel = REL_LOGIN_FACEBOOK

    def __init__(self, user, req):
        self.request = req
        self.user = user

    def __call__(self):
        if not self.user.username:
            return None
        return Link(self.request.route_path('logon.facebook.oauth1',
                                            _query={'username': self.user.username}),
                    rel=self.rel)


@component.adapter(nti_interfaces.IFacebookUser, pyramid.interfaces.IRequest)
class _SimpleExistingUserFacebookLinkProvider(_SimpleMissingUserFacebookLinkProvider):
    pass


def _prepare_oid_link(request, username, rel, params=()):
    query = dict(params)
    if 'oidcsum' not in query:
        query['oidcsum'] = _checksum(username)
    query['username'] = username

    title = None
    if 'openid' in query:
        # We have to derive the title, we can't supply it from
        # the link provider because the link provider changes
        # when IMissingUser becomes a real user, and it's just one
        # for all open ids
        idurl_domain = urllib_parse.urlparse(query['openid']).netloc
        if idurl_domain:
            # Strip down to just the root domain. This assumes
            # we get a valid domain, at least 'example.com'
            idurl_domain = '.'.join(idurl_domain.split('.')[-2:])
            title = _(u'Sign in with ${domain}',
                      mapping={'domain': idurl_domain})
            # TODO: Make this automatic
            title = translate(title, context=request)

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

    def params_for(self, *unused_args, **unused_kwargs):
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

    def params_for(self, *unused_args, **unused_kwargs):
        aops_username = self.user.username.split('@')[0]
        # Larry says:
        # > http://<username>.openid.artofproblemsolving.com
        # > http://openid.artofproblemsolving.com/<username>
        # > http://<username>.openid.aops.com
        # > http://openid.aops.com/<username>
        # But 3 definitely doesn't work. 1 and 4 do. We use 4
        return {'openid': 'http://openid.aops.com/%s' % aops_username}

    def getUsername(self, idurl, *unused_args, **unused_kwargs):
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

    #: When we go to production, this will change to
    #: secure....
    _BASE_URL = 'https://demo.mallowstreet.com/Mallowstreet/OpenID/User.aspx/%s'

    def params_for(self, user):
        # strip the trailing '@mallowstreet.com', preserving any previous
        # portion that looked like an email
        mallow_username = '@'.join(user.username.split('@')[0:-1])
        return {'openid': self._BASE_URL % mallow_username}

    def getUsername(self, idurl, *unused_args, **unused_kwargs):
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

    def toExternalObject(self, **kwargs):
        return {CLASS: self.__external_class_name__,
                MIMETYPE: self.mime_type,
                LINKS: self.links}


def _create_failure_response(request, failure=None, error=None, error_factory=hexc.HTTPUnauthorized):
    if error:
        logger.info("Authentication error (%s)", error)
    return _forgetting(request, 'failure', error_factory,
                       redirect_value=failure, error=error)
create_failure_response = _create_failure_response

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

    # Make it the same to avoid confusing things that only get the request,
    # e.g., event listeners
    request.response = response
    userid = userid or request.authenticated_userid
    logon_userid_with_request(userid, request, response)
    return response
create_success_response = _create_success_response

def _query_impersonation_decider(request, username, name=''):
    decider = component.queryAdapter(request, IImpersonationDecider, name)
    if decider:
        decider.validate_impersonation_target(username)


def _can_impersonate(request, username):
    """
    Query a set of IImpersonationDeciders to
    verify if impersonation of the given username should
    be allowed for the request
    """

    # verify by domain first
    if '@' in username:
        domain = username.split('@', 1)[-1]
        if domain:
            # May want to consider prefixing this
            _query_impersonation_decider(request, username, name=domain)

    # now by username
    _query_impersonation_decider(request, username, name=username)

    # now by global adapter
    _query_impersonation_decider(request, username)


def _specified_username_logon(request, allow_no_username=True, require_matching_username=True,
                              audit=False, desired_username=None):
    # This code handles both an existing logged on user and not
    remote_user = _authenticated_user(request)
    if not remote_user:
        # not authenticated or does not exist
        return _create_failure_response(request)

    if not desired_username:
        try:
            desired_usernames = request.params.getall('username') or []
        except AttributeError:
            # Nark. For test code. It's hard to always be able to use a real
            # MultiDict
            desired_usernames = request.params.get('username', ())
            if desired_usernames:
                desired_usernames = [desired_usernames]

        if len(desired_usernames) > 1:
            return _create_failure_response(request,
                                            error_factory=hexc.HTTPBadRequest,
                                            error=_(u'Multiple usernames'))

        if desired_usernames:
            desired_username = desired_usernames[0].lower()
        elif allow_no_username:
            desired_username = remote_user.username.lower()
        else:
            return _create_failure_response(request,
                                            error_factory=hexc.HTTPBadRequest,
                                            error=_(u'No username'))

    if require_matching_username and desired_username != remote_user.username.lower():
        # Usually a cookie/param mismatch
        response = _create_failure_response(request)
    else:
        try:
            # If we're impersonating, record that fact in the cookie.
            # This will later show up in the environment and error/feedback
            # reports. This is a pretty basic version of that; if we use
            # it for anything more than display, we need to formalize it more.
            if desired_username != remote_user.username.lower():
                # check if we are allowed to impersonate first
                try:
                    _can_impersonate(request, desired_username)
                except ValueError:
                    return _create_failure_response(request,
                                                    error_factory=hexc.HTTPForbidden)
                user_data = {}
                user_data['username'] = str(remote_user.username.lower())
                request.environ['REMOTE_USER_DATA'] = user_data

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


@interface.implementer(IImpersonationDecider)
class DenyImpersonation(object):
    """
    An impersonation decider that always denies
    """

    def __init__(self, request):
        pass

    def validate_impersonation_target(self, userid):
        raise ValueError()


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
    # Note that this also accepts the authentication cookie, not just the
    # Basic auth
    return _specified_username_logon(request)


@view_config(route_name=REL_LOGIN,
             request_method='GET',
             renderer='rest')
def generic_logon(request):
    """
    Found at the path in :const:`REL_LOGIN`, this will log a user regardless of how they are
    identified and authenticated.

    The request parameter `success` can be used to indicate a redirection upon successful logon.
    Likewise, the parameter `failure` can be used for redirection on a failed attempt.
    """
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

    settings = {
        'openid.param_field_name': _OPENID_FIELD_NAME,
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
        openid = params.get('openid.identity', params.get('openid')) \
              or 'https://www.google.com/accounts/o8/id'

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
                                             # to
                                             # carry
                                             # through
                                             # HTTPS
                                             # info
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
        # failed to pass required params. For example, the openid_param_name
        # might not match
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
                error = _(u"The request was canceled by the remote server.")
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


def deal_with_external_account(request, username, fname, lname, email, idurl, iface,
                               user_factory, realname=None, ext_values=None):
    """
    Finds or creates an account based on an external authentication.

    :param username: The login name the user typed. Must be globally unique, and
            should be in the form of an email.
    :param email: The email the user provides. Should be an email. Not required.
    :param idul: The URL that identifies the user on the external system.
    :param iface: The interface that the user object will implement.
    :return: The user object
    """
    if ext_values is None:
        ext_values = dict()
    dataserver = component.getUtility(nti_interfaces.IDataserver)
    user = User.get_user(username=username, dataserver=dataserver)
    url_attr = iface.names()[0] if iface and iface.names() and idurl else None
    if user:
        if iface and not iface.providedBy(user):
            interface.alsoProvides(user, iface)
            if url_attr:
                setattr(user, url_attr, idurl)
                descriptions = lifecycleevent.Attributes(iface, url_attr)
                lifecycleevent.modified(user, descriptions)
        if url_attr:
            assert getattr(user, url_attr) == idurl
    else:
        # When creating, we go through the same steps as account_creation_views,
        # guaranteeing the proper validation
        ext_values.update({'Username': username, 'email': email})
        if not realname:
            if fname and lname:
                realname = fname + ' ' + lname

        if realname:
            ext_values['realname'] = realname
        if url_attr:
            ext_values[url_attr] = idurl

        require_password = False
        from .account_creation_views import _create_user  # XXX A bit scuzzy

        # This fires lifecycleevent.IObjectCreatedEvent and IObjectAddedEvent. The oldParent attribute
        # will be None
        user = _create_user(request, ext_values,
                            require_password=require_password,
                            user_factory=user_factory)
        __traceback_info__ = request, user_factory, iface, user

        if url_attr:
            # doesn't get read from the external value right now
            assert getattr(user, url_attr) is None
            setattr(user, url_attr, idurl)
            assert getattr(user, url_attr) == idurl
        if iface:
            assert iface.providedBy(user)
        # We manually fire the user_created event. See account_creation_views
        notify(UserCreatedWithRequestEvent(user, request))
    return user

_deal_with_external_account = deal_with_external_account


from zlib import crc32


def _checksum(username):
    return str(crc32(username))  # must be stable across machines


def _openidcallback(unused_context, request, success_dict):
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
    # this using a list (see openid.extensions.ax.AXKeyValueMessage.get and
    # pyramid_openid.view.process_provider_response)
    ax_dict = success_dict.get('ax', {})
    fname = ax_dict.get('firstname', ('',))[0]
    lname = ax_dict.get('lastname', ('',))[0]
    email = ax_dict.get('email', ('',))[0]
    content_roles = ax_dict.get('content_roles', ())

    idurl_domain = urllib_parse.urlparse(idurl).netloc
    username_provider = component.queryMultiAdapter((None, request),
                                                    ILogonUsernameFromIdentityURLProvider,
                                                    name=idurl_domain)
    if username_provider:
        username = username_provider.getUsername(idurl, success_dict)
    elif email:
        username = email
    else:
        return _create_failure_response(request,
                                        error=_(u'Unable to derive username.'))

    if _checksum(username) != oidcsum:
        logger.warn("Checksum mismatch. Logged in multiple times? %s %s username=%s prov=%s",
                    oidcsum, success_dict, username, username_provider)
        return _create_failure_response(request, error='Username/Email checksum mismatch')

    try:
        # TODO: Make this look the interface and factory to assign up by name (something in the idurl?)
        # That way we can automatically assign an IAoPSUser and use a
        # users.AoPSUser
        the_user = _deal_with_external_account(request,
                                               username=username,
                                               fname=fname,
                                               lname=lname,
                                               email=email,
                                               idurl=idurl,
                                               iface=nti_interfaces.IOpenIdUser,
                                               user_factory=OpenIdUser.create_user)
        notify(OpenIDUserCreatedEvent(the_user, idurl, content_roles))
    except hexc.HTTPError:
        raise
    except Exception as e:
        return _create_failure_response(request, error=str(e))

    return _create_success_response(request, userid=the_user.username)


@component.adapter(nti_interfaces.IUser, IUserLogonEvent)
def _user_did_logon(user, event):
    request = event.request
    request.environ['nti.request_had_transaction_side_effects'] = 'True'
    # Do not update on impersonation request
    # SSO paths do not have an authenticated_userid at this point.
    auth_username = event.request and event.request.authenticated_userid
    if auth_username is None or auth_username == user.username:
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
    our_uri = urllib_parse.quote(request.route_url('logon.facebook.oauth2'))
    # We seem incapable of sending any parameters with the redirect_uri. If we do,
    # then the validation step 400's. Thus we resort to the session
    for k in ('success', 'failure'):
        if request.params.get(k):
            request.session['facebook.' + k] = request.params.get(k)

    request.session['facebook.username'] = request.params.get('username')
    data = (FB_DIAG_OAUTH, app_id, our_uri)
    redir_to = '%s?client_id=%s&redirect_uri=%s&scope=email' % data
    return hexc.HTTPSeeOther(location=redir_to)


@view_config(route_name='logon.facebook.oauth2', request_method='GET')
def facebook_oauth2(request):

    if 'error' in request.params:
        return _create_failure_response(request,
                                        request.session.get(
                                            'facebook.failure'),
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
                                        request.session.get(
                                            'facebook.failure'),
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
                                        request.session.get(
                                            'facebook.failure'),
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
