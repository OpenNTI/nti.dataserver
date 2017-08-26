#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Plugins for :mod:`repoze.who` that primarily handle authentication.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.pluggableauth.interfaces import IAuthenticatorPlugin

from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IAuthenticator

from nti.app.authentication.interfaces import IIdentifiedUserTokenAuthenticator


@interface.implementer(IAuthenticator)
class DataserverGlobalUsersAuthenticatorPlugin(object):

    def authenticate(self, unused_environ, identity):
        try:
            plugin = component.getUtility(IAuthenticatorPlugin,
                                          name="Dataserver Global User Authenticator")
            return plugin.authenticateCredentials(identity).id
        except (KeyError, AttributeError, LookupError):  # pragma: no cover
            return None


@interface.implementer(IAuthenticator,
                       IIdentifier)
class KnownUrlTokenBasedAuthenticator(object):
    """
    A :mod:`repoze.who` plugin that acts in the role of identifier
    (determining who the remote user is claiming to be)
    as well as authenticator (matching the claimed remote credentials
    to the real credentials). This information is not sent in the
    headers (Authenticate or Cookie) but instead, for the use of
    copy-and-paste, retrieved directly from query parameters in the
    URL (specifically, the 'token' parameter).

    Because it is part of the URL, this information is visible in the
    logs for the entire HTTP pipeline. To limit the overuse of this, we
    only want to allow it for particular URLs, as based on the path.
    """

    # We actually piggyback off the authtkt implementation, using
    # a version of the user's password as the 'user data'

    from paste.request import parse_dict_querystring
    parse_dict_querystring = staticmethod(parse_dict_querystring)

    def __init__(self, secret, allowed_views=()):
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

    def identify(self, environ):
        # Obviously if there is no token we can't identify
        if 'QUERY_STRING' not in environ or 'token' not in environ['QUERY_STRING']:
            return
        if 'PATH_INFO' not in environ:
            return
        if not any((environ['PATH_INFO'].endswith(view) for view in self.allowed_views)):
            return

        query_dict = self.parse_dict_querystring(environ)
        token = query_dict['token']
        authenticator = component.getAdapter(self.secret, 
											 IIdentifiedUserTokenAuthenticator)
        identity = authenticator.getIdentityFromToken(token)
        if identity is not None:
            environ['IDENTITY_TYPE'] = 'token'
        return identity

    def forget(self, unused_environ, unused_identity):  # pragma: no cover
        return []

    def remember(self, unused_environ, unused_identity):  # pragma: no cover
        return []

    def authenticate(self, environ, identity):
        if environ.get('IDENTITY_TYPE') != 'token':
            return

        environ['AUTH_TYPE'] = 'token'
        authenticator = component.getAdapter(self.secret, 
											 IIdentifiedUserTokenAuthenticator)
        return authenticator.identityIsValid(identity)
