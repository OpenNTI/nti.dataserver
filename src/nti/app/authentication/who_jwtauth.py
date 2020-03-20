#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import binascii

from jwt import decode

from jwt.exceptions import DecodeError

from zope import component

from repoze.who.plugins.basicauth import BasicAuthPlugin

from nti.appserver.interfaces import IApplicationSettings

logger = __import__('logging').getLogger(__name__)


JWT_ALGS = ['HS256']


class JWTAuthPlugin(BasicAuthPlugin):
    """
    An auth plugin that parses a "Bearer" authorization token
    into a jwt payload.
    """

    def _get_secret(self, default_secret='jwt-secret'):
        settings = component.queryUtility(IApplicationSettings) or {}
        secret_key = settings.get('jwt_secret', default_secret)
        return secret_key

    def identify(self, environ):
        auth = environ.get('HTTP_AUTHORIZATION', '')

        try:
            auth = auth.strip()
            authmeth, auth = auth.split(b' ', 1)
        except (ValueError, AttributeError):
            return None
        if authmeth.lower() == b'bearer':
            secret = self._get_secret()
            try:
                auth = auth.strip()
                # This will validate the payload, including the
                # expiration date. We course also whitelist the issuer here.
                auth = decode(auth, secret, algorithms=JWT_ALGS)
            except DecodeError:
                return None
            return auth
        return None
