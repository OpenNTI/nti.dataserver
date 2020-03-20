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
class DataserverJWTAuthenticatorPlugin(object):
    """
    Authenticates jwt bearer tokens.
    """

    def authenticateCredentials(self, credentials):
        """
        Validate the user and token.
        """
        login = credentials.get('login')
        user = User.get_user(login)
        if user is None:
            return None
        return self.principalInfo(login)

    def principalInfo(self, pid):
        user = User.get_user(pid)
        if user is not None:
            return PrincipalInfo(pid, pid, pid, pid)
