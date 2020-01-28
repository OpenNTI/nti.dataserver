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

from zope import interface

from nti.app.authentication.user_token import DefaultIdentifiedUserTokenAuthenticator
from nti.app.authentication.user_token import DefaultIdentifiedAdminUserTokenAuthenticator

from nti.app.authentication.who_authenticators import KnownUrlTokenBasedAuthenticator
from nti.app.authentication.who_authenticators import AdminUserTokenBasedAuthenticator

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.users.interfaces import IAdminUserToken
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

    @WithMockDSTrans
    @fudge.patch('zope.component.getAdapter')
    def test_identify_admin_token(self, mock_get):
        """
        The admin token authenticator will allow access to any view with a
        valid admin token for our user.
        """
        plugin = AdminUserTokenBasedAuthenticator('secret')

        username = u'admin_token_username'
        valid_scope = u'admin:scope'
        user = User.create_user(username=username)

        # Create token
        container = IUserTokenContainer(user, None)
        user_token = UserToken(title=u"title",
                               description=u"desc",
                               scopes=(valid_scope,))
        container.store_token(user_token)

        tokens = DefaultIdentifiedAdminUserTokenAuthenticator('secret')
        mock_get.is_callable().returns(tokens)

        token = tokens.getTokenForUserId(username, valid_scope)
        environ = {'QUERY_STRING': 'token=' + token,
                   'PATH_INFO': '/arbitrary_view'}

        # No token
        identity = plugin.identify(environ)
        assert_that(plugin.authenticate(environ, identity),
                    none())

        # Invalid token
        environ['X-NTI-ADMIN-TOKEN'] = 'invalid_token'
        identity = plugin.identify(environ)
        assert_that(plugin.authenticate(environ, identity),
                    none())

        # Valid token but not admin
        environ['X-NTI-ADMIN-TOKEN'] = token
        identity = plugin.identify(environ)
        assert_that(plugin.authenticate(environ, identity),
                    none())

        # Valid token
        interface.alsoProvides(user_token, IAdminUserToken)
        environ['X-NTI-ADMIN-TOKEN'] = token
        identity = plugin.identify(environ)
        assert_that(plugin.authenticate(environ, identity),
                    is_(username))

        # Invalidate
        container.clear()
        assert_that(plugin.authenticate(environ, identity),
                    is_(none()))

        # Restore
        container.store_token(user_token)
        identity = plugin.identify(environ)
        assert_that(plugin.authenticate(environ, identity),
                    is_(username))

        # Invalid token but we have admin token stored
        environ['X-NTI-ADMIN-TOKEN'] = 'invalid_token'
        identity = plugin.identify(environ)
        assert_that(plugin.authenticate(environ, identity),
                    none())
