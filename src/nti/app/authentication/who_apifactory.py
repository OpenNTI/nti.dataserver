#!/Sr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# Like Pyramid 1.4+, cause Paste's AuthTkt cookies to use the more secure
# SHA512 algorithm instead of the weaker MD5 (actually, repoze.who, now)
import nti.monkey.patch_paste_auth_tkt_sha512_on_import
nti.monkey.patch_paste_auth_tkt_sha512_on_import.patch()

from zope import component

from repoze.who.api import APIFactory

from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin

from nti.app.authentication import user_can_login

from nti.app.authentication.who_authenticators import KnownUrlTokenBasedAuthenticator
from nti.app.authentication.who_authenticators import DataserverJWTAuthenticatorPlugin
from nti.app.authentication.who_authenticators import DataserverGlobalUsersAuthenticatorPlugin

from nti.app.authentication.who_basicauth import BasicAuthPlugin
from nti.app.authentication.who_basicauth import ApplicationBasicAuthPlugin

from nti.app.authentication.who_classifiers import application_request_classifier
from nti.app.authentication.who_classifiers import forbidden_or_missing_challenge_decider

from nti.app.authentication.who_redirector import BrowserRedirectorPlugin

from nti.app.authentication.who_jwtauth import JWTAuthPlugin

from nti.appserver.interfaces import IApplicationSettings

ONE_DAY = 24 * 60 * 60
ONE_WEEK = 7 * ONE_DAY

logger = __import__('logging').getLogger(__name__)


def create_who_apifactory(secure_cookies=True,
                          cookie_secret='$Id$',
                          cookie_timeout=ONE_WEEK,
                          token_allowed_views=('feed.rss', 'feed.atom')):
    """
    :param bool secure_cookies: If ``True`` (the default), then any cookies
            we create will only be sent over SSL and will additionally have the 'HttpOnly'
            flag set, preventing them from being subject to cross-site vulnerabilities.
            This must be explicitly turned off if not desired.
    :param str cookie_secret: The value used to encrypt cookies. Must be the same on
            all instances in a given environment, but should be different in different
            environments.

    :return: An implementation of :class:`IAPIFactory` that additionally has
            an attribute ``default_identifier_name`` giving the name of the default
            identifier that should be used for remembering. This will be a cookie-based
            authenticator.
    """

    # Note that the cookie name and header names needs to be bytes,
    # not unicode. Otherwise we wind up with unicode objects in the
    # headers, which are supposed to be ascii. Things like the Cookie
    # module (used by webtest) then fail. Actually, not bytes specifically,
    # but the native string type.
    basicauth = BasicAuthPlugin('NTI')
    basicauth_interactive = ApplicationBasicAuthPlugin('NTI')
    jwtauth = JWTAuthPlugin('NTI')

    auth_tkt = AuthTktCookiePlugin(cookie_secret,
                                   'nti.auth_tkt',
                                   secure=secure_cookies,
                                   timeout=cookie_timeout,
                                   reissue_time=600,
                                   # For extra safety, we can refuse to return authenticated ids
                                   # if they don't exist or are denied logon.
                                   # If we are called too early, outside the site,
                                   # this can raise an exception, but the only place that
                                   # matters, logging, already deals with it (gunicorn.py).
                                   # Because it's an exception, it prevents
                                   # any of the caching from kicking in.
                                   userid_checker=user_can_login)

    # Create a identifier and authenticator that
    # can be used only for certain views, here, our
    # known RSS/Atom views. This is clearly not very configurable.
    token_tkt = KnownUrlTokenBasedAuthenticator(cookie_secret,
                                                allowed_views=token_allowed_views)

    # For browsers (NOT application browsers), we want to do authentication via a
    # redirect to the login app.
    try:
        settings = component.getUtility(IApplicationSettings)
    except LookupError:
        settings = {}
    login_root = settings.get('login_app_root', '/login/')

    # A plugin that will redirect to the login app, telling the login
    # app what path to return to (where we came from)
    redirector = BrowserRedirectorPlugin(str(login_root),
                                         came_from_param='return')

    # Claimed identity (username) can come from the cookie,
    # or HTTP Basic auth, or in special cases, from the token query param
    # The plugin that identified a request will be the one asked to forget
    # it if a challenge is issued.
    identifiers = [('auth_tkt', auth_tkt)]
    identifiers.append(('basicauth-interactive', basicauth_interactive))
    identifiers.append(('basicauth', basicauth))
    identifiers.append(('jwtauth', jwtauth))
    identifiers.append(('token_tkt', token_tkt))

    # Confirmation/authentication can come from the cookie (encryption)
    # Or possibly HTTP Basic auth, HTTP Bearer tokens, or in special cases, from the
    # token query param
    authenticators = [('auth_tkt', auth_tkt)]
    authenticators.append(('htpasswd', DataserverGlobalUsersAuthenticatorPlugin()))
    authenticators.append(('jwt', DataserverJWTAuthenticatorPlugin()))
    authenticators.append(('token_tkt', token_tkt))

    # Order matters when multiple plugins accept the classification
    # of the request; the first plugin that returns a result from
    # its challenge() method stops iteration.
    challengers = [('browser-redirector', redirector)]
    challengers.append(('basicauth-interactive', basicauth_interactive))
    challengers.append(('basicauth', basicauth))
    challengers.append(('jwtauth', jwtauth))

    mdproviders = []

    api_factory = APIFactory(identifiers,
                             authenticators,
                             challengers,
                             mdproviders,
                             application_request_classifier,
                             forbidden_or_missing_challenge_decider,
                             'REMOTE_USER',  # environment remote user key
                             None)  # No logger, leads to infinite loops
    api_factory.default_identifier_name = 'auth_tkt'
    return api_factory
