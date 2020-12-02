#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integrations with :mod:`zope.pluggableauth``

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.authentication.interfaces import ILoginPassword

from zope.pluggableauth.factories import PrincipalInfo

from zope.pluggableauth.interfaces import IAuthenticatorPlugin

from nti.app.authentication import user_can_login

from nti.dataserver.users.interfaces import IAuthToken
from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.users import User

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IAuthenticatorPlugin)
class DataserverUsersAuthenticatorPlugin(object):
    """
    Globally authenticates principals.
    """

    def authenticateCredentials(self, credentials):
        """
        Authenticate the user based on whitelist and presented
        credentials.

        The credentials are either a dictionary containing "login" and
        \"password\", or an instance of :class:`.ILoginPassword`
        """
        login = None
        password = None
        if ILoginPassword.providedBy(credentials):
            login = credentials.getLogin()
            password = credentials.getPassword()
        else:
            login = credentials.get('login')
            password = credentials.get('password')

        if not user_can_login(login) or not password:
            return None

        user = User.get_user(login)
        if user is None or user.password is None:
            return None

        if user.password.checkPassword(password):
            return self.principalInfo(login)

    def principalInfo(self, pid):
        user = User.get_user(pid)
        if user is not None:
            # 1) Better title and description
            return PrincipalInfo(pid, pid, pid, pid)


@interface.implementer(IAuthenticatorPlugin)
class DataserverTokenAuthenticatorPlugin(object):
    """
    Authenticates bearer tokens. The only tokens accepted must be a
    :class:`nti.dataserver.users.interfaces.IAuthToken`.
    """

    def _valid_token(self, user, target_token):
        admin_tokens = ()
        if user is not None:
            token_container = IUserTokenContainer(user)
            admin_tokens = [x.token for x in token_container.get_valid_tokens() \
                            if IAuthToken.providedBy(x)]
        return target_token in admin_tokens

    def authenticateCredentials(self, credentials):
        """
        Validate the user and token.
        """
        login = credentials.get('login')
        token = credentials.get('token')

        user = User.get_user(login)
        if user is None or token is None:
            return None
        if      self._valid_token(user, token) \
            and user_can_login(user):
            return self.principalInfo(login)

    def principalInfo(self, pid):
        user = User.get_user(pid)
        if user is not None:
            # 1) Better title and description
            return PrincipalInfo(pid, pid, pid, pid)
