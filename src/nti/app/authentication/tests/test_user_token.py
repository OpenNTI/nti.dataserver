#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that

import unittest

from datetime import datetime
from datetime import timedelta

from nti.app.authentication.user_token import DefaultIdentifiedUserTokenAuthenticator

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.tokens import UserToken

from nti.dataserver.users.users import User


class TestUserToken(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_tokens(self):
        username = u'token_username'
        valid_scope = u'user:scope'
        user = User.create_user(username=username)
        plugin = DefaultIdentifiedUserTokenAuthenticator()
        assert_that(plugin.getTokenForUserId(username, 'dne:scope'), none())

        # Create token
        container = IUserTokenContainer(user, None)
        assert_that(container, has_length(0))
        user_token = UserToken(title=u"title",
                               description=u"desc",
                               scopes=(valid_scope,))
        container.store_token(user_token)

        assert_that(plugin.getTokenForUserId(username, 'dne:scope'), none())
        token = plugin.getTokenForUserId(username, valid_scope)
        assert_that(token, not_none())

        identity = plugin.getIdentityFromToken(token)
        assert_that(plugin.tokenIsValidForUserid(token, username),
                    is_(username))

        assert_that(plugin.identityIsValid(identity),
                    is_(username))

        # Token with future expiration date
        user_token.expiration_date = datetime.utcnow() + timedelta(seconds=30)
        assert_that(plugin.tokenIsValidForUserid(token, username),
                    is_(username))
        assert_that(plugin.identityIsValid(identity),
                    is_(username))

        # Token expired
        user_token.expiration_date = datetime.utcnow() - timedelta(seconds=30)
        assert_that(plugin.tokenIsValidForUserid(token, username),
                    is_(none()))
        assert_that(plugin.identityIsValid(identity),
                    is_(none()))

        # Token gone
        container.clear()
        assert_that(plugin.tokenIsValidForUserid(token, username),
                    is_(none()))
        assert_that(plugin.identityIsValid(identity),
                    is_(none()))

