#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import binascii

from repoze.who.plugins.basicauth import decodebytes
from repoze.who.plugins.basicauth import must_decode
from repoze.who.plugins.basicauth import BasicAuthPlugin

logger = __import__('logging').getLogger(__name__)


class TokenAuthPlugin(BasicAuthPlugin):
    """
    An auth plugin that parses a "Bearer" authorization token
    into a jwt payload.
    """

    def identify(self, environ):
        auth = environ.get('HTTP_AUTHORIZATION', '')

        try:
            auth = auth.strip()
            authmeth, auth = auth.split(b' ', 1)
        except (ValueError, AttributeError):
            return None
        if authmeth.lower() == b'bearer':
            try:
                auth = auth.strip()
                auth = decodebytes(auth)
            except binascii.Error: # can't decode
                return None
            try:
                login, token = auth.split(b':', 1)
            except ValueError: # not enough values to unpack
                return None
            auth = {'login': must_decode(login),
                    'token': must_decode(token)}
            return auth
        return None
