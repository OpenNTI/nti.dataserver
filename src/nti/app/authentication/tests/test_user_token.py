#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that

import unittest

import fudge

from nti.app.authentication.user_token import DefaultIdentifiedUserTokenAuthenticator


class TestUserToken(unittest.TestCase):

    @fudge.patch('nti.app.authentication.user_token.DefaultIdentifiedUserTokenAuthenticator._get_user_password')
    def test_identify_token(self, mock_pwd):
        mock_pwd.is_callable().returns_fake().provides('getPassword').returns('abcde')
        plugin = DefaultIdentifiedUserTokenAuthenticator()

        token = plugin.getTokenForUserId('user')

        identity = plugin.getIdentityFromToken(token)
        assert_that(plugin.tokenIsValidForUserid(token, 'user'),
                    is_('user'))

        assert_that(plugin.identityIsValid(identity),
                    is_('user'))

        # Password change behind the scenes
        mock_pwd.is_callable().returns_fake().provides('getPassword').returns('1234')
        assert_that(plugin.tokenIsValidForUserid(token, 'user'),
                    is_(none()))
