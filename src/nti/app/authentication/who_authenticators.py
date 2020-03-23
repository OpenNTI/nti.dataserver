#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Plugins for :mod:`repoze.who` that primarily handle authentication.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from jwt import decode

from jwt.exceptions import DecodeError

from zope import component
from zope import interface

from zope.pluggableauth.interfaces import IAuthenticatorPlugin

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IAuthenticator

from nti.app.authentication.interfaces import IIdentifiedUserTokenAuthenticator

from nti.dataserver.authorization import ROLE_ADMIN

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.users import User

logger = __import__('logging').getLogger(__name__)


JWT_ALGS = ['HS256']


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
class DataserverJWTAuthenticator(object):

    def __init__(self, secret):
        """
        Creates a combo :class:`.IIdentifier` and :class:`.IAuthenticator`
        using an auth-tkt like token.

        :param string secret: The encryption secret. May be the same as the
                auth_tkt secret.
        """
        self.secret = secret

    def identify(self, environ):
        auth = environ.get('HTTP_AUTHORIZATION', '')
        result = None
        try:
            auth = auth.strip()
            authmeth, auth = auth.split(b' ', 1)
        except (ValueError, AttributeError):
            return None
        if authmeth.lower() == b'bearer':
            try:
                auth = auth.strip()
                # This will validate the payload, including the
                # expiration date. We course also whitelist the issuer here.
                auth = decode(auth, self.secret, algorithms=JWT_ALGS)
            except DecodeError:
                pass
            else:
                result = auth
                environ['IDENTITY_TYPE'] = 'jwt_token'
        return result

    def forget(self, unused_environ, unused_identity):  # pragma: no cover
        return []

    def remember(self, unused_environ, unused_identity):  # pragma: no cover
        return []

    def _make_admin(self, user):
        """
        Assign the NT admin role to this user.
        """
        dataserver = component.getUtility(IDataserver)
        ds_folder = dataserver.root_folder['dataserver2']
        ds_role_manager = IPrincipalRoleManager(ds_folder)
        ds_role_manager.assignRoleToPrincipal(ROLE_ADMIN.id, user.username)

    def authenticate(self, environ, identity):
        if environ.get('IDENTITY_TYPE') != 'jwt_token':
            return
        try:
            username = identity['login']
        except KeyError:
            return

        result = None
        user = User.get_user(username)
        if user is not None:
            result = user.username
        elif 'create' in identity:
            # site user restrictions etc, mark request
            logger.info("Creating user via JWT (%s)",
                        username)
            try:
                # Create a user without credentials
                user = User.create_user(username=username,
                                        external_value=identity)
                result = username
            except:
                # Overly broad, can we just catch validation errors?
                logger.exception("Error during JWT provisioning (%s)",
                                 identity)

        if 'admin' in identity and user is not None:
            self._make_admin(user)
        return result


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

    def _get_token(self, environ):
        # Obviously if there is no token we can't identify
        if 'QUERY_STRING' not in environ or 'token' not in environ['QUERY_STRING']:
            return
        if 'PATH_INFO' not in environ:
            return
        if not any((environ['PATH_INFO'].endswith(view) for view in self.allowed_views)):
            return

        query_dict = self.parse_dict_querystring(environ)
        token = query_dict['token']
        return token

    def identify(self, environ):
        token = self._get_token(environ)
        if not token:
            return
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
