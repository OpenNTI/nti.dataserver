#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that
from hamcrest import has_entries

import unittest

from zope import component
from zope import interface

from nti.app.authentication.pluggableauth import DataserverTokenAuthenticatorPlugin

from nti.app.authentication.who_authenticators import DataserverTokenAuthenticator

from nti.app.authentication.who_tokenauth import TokenAuthPlugin

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.users.interfaces import IAdminUserToken
from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.tokens import UserToken

from nti.dataserver.users.users import User


class TestTokenAuth(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def setUp(self):
        self.token_auth_plugin = DataserverTokenAuthenticatorPlugin()
        component.getGlobalSiteManager().registerUtility(self.token_auth_plugin,
                                                         name="Dataserver Token Authenticator")

    @WithMockDSTrans
    def test_token_auth(self):
        username = u'token_auth_username'
        token_val = 'testtoken'
        encoded_creds = 'dG9rZW5fYXV0aF91c2VybmFtZTp0ZXN0dG9rZW4=\n'
        user = User.create_user(username=username)

        environ = dict()
        token_auth = TokenAuthPlugin('NTI')

        identity = token_auth.identify(environ)
        assert_that(identity, none())

        creds = 'InvalidCredentials'
        environ['HTTP_AUTHORIZATION'] = creds
        identity = token_auth.identify(environ)
        assert_that(identity, none())

        environ['HTTP_AUTHORIZATION'] = 'Basic %s' % encoded_creds
        identity = token_auth.identify(environ)
        assert_that(identity, none())

        environ['HTTP_AUTHORIZATION'] = 'Bearer %s' % encoded_creds
        identity = token_auth.identify(environ)
        assert_that(identity, has_entries('login', username,
                                          'token', token_val))

        environ['HTTP_AUTHORIZATION'] = ' BEARER %s' % encoded_creds
        identity = token_auth.identify(environ)
        assert_that(identity, has_entries('login', username,
                                          'token', token_val))

        # Auth with invalid/missing tokens
        auth = DataserverTokenAuthenticator()
        prin_info = auth.authenticate(environ, {})
        assert_that(prin_info, none())

        bad_identity = dict(identity)
        bad_identity.pop('token')
        prin_info = auth.authenticate(environ, bad_identity)
        assert_that(prin_info, none())

        bad_identity['token'] = 'incorrect_token'
        prin_info = auth.authenticate(environ, bad_identity)
        assert_that(prin_info, none())

        # Create a token for our user
        container = IUserTokenContainer(user, None)
        user_token = UserToken(title=u"title",
                               description=u"desc")
        user_token.token = token_val
        container.store_token(user_token)

        # Still no match
        prin_info = auth.authenticate(environ, bad_identity)
        assert_that(prin_info, none())

        # Now with valid, correct identity but not an admin token
        prin_info = auth.authenticate(environ, identity)
        assert_that(prin_info, none())

        # Now a valid match
        interface.alsoProvides(user_token, IAdminUserToken)
        prin_info = auth.authenticate(environ, identity)
        assert_that(prin_info, is_(username))
