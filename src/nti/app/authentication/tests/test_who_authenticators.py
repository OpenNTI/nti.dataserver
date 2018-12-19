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

from nti.app.authentication.who_authenticators import KnownUrlTokenBasedAuthenticator

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.tokens import UserToken

from nti.dataserver.users.users import User


class TestKnownUrlTokenBasedAuthenticator(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def setUp(self):
        self.plugin = KnownUrlTokenBasedAuthenticator('secret',
													  allowed_views=('feed.atom', 'test'))

    def test_identify_empty_environ(self):
        assert_that(self.plugin.identify({}), is_(none()))
        assert_that(self.plugin.identify({'QUERY_STRING': ''}), is_(none()))

        assert_that(self.plugin.identify({'QUERY_STRING': 'token=foo'}),
                    is_(none()))

    def test_identify_wrong_view(self):
        assert_that(self.plugin.identify({'QUERY_STRING': 'token',
                                          'PATH_INFO': '/foo/bar'}),
                    is_(none()))

    @WithMockDSTrans
    @fudge.patch('zope.component.getAdapter')
    def test_identify_token(self, mock_get):
        username = u'token_username'
        valid_scope = u'user:scope'
        user = User.create_user(username=username)

        # Create token
        container = IUserTokenContainer(user, None)
        user_token = UserToken(title=u"title",
                               description=u"desc",
                               scopes=(valid_scope,))
        container.store_token(user_token)

        tokens = DefaultIdentifiedUserTokenAuthenticator('secret')
        mock_get.is_callable().returns(tokens)

        token = tokens.getTokenForUserId(username, valid_scope)
        environ = {'QUERY_STRING': 'token=' + token,
                   'PATH_INFO': '/feed.atom'}

        identity = self.plugin.identify(environ)
        assert_that(self.plugin.authenticate(environ, identity),
                    is_(username))

        # Invalidate
        container.clear()
        assert_that(self.plugin.authenticate(environ, identity),
                    is_(none()))

        # Restore
        container.store_token(user_token)
        identity = self.plugin.identify(environ)
        assert_that(self.plugin.authenticate(environ, identity),
                    is_(username))
