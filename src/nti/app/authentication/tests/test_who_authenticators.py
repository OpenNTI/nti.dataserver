#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that

import unittest

import time
import fudge

from jwt import encode

from zope import component

from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.authentication.user_token import DefaultIdentifiedUserTokenAuthenticator

from nti.app.authentication.who_authenticators import _get_jwt_max_age
from nti.app.authentication.who_authenticators import DataserverJWTAuthenticator
from nti.app.authentication.who_authenticators import KnownUrlTokenBasedAuthenticator

from nti.dataserver.authorization import ROLE_ADMIN

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.tokens import UserToken

from nti.dataserver.users.users import User

from nti.testing.time import time_monotonically_increases


class TestKnownUrlTokenBasedAuthenticator(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def setUp(self):
        self.plugin = KnownUrlTokenBasedAuthenticator('secret',
													  allowed_views=('feed.atom', 'test'))
        self.jwt_auth = DataserverJWTAuthenticator(secret='jwt_secret')

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


class TestJWTAuthenticator(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_empty_environ(self):
        jwt_auth = DataserverJWTAuthenticator(secret='jwt_secret')
        assert_that(jwt_auth.authenticate({}, None), is_(none()))
        assert_that(jwt_auth.identify({}), is_(none()))
        assert_that(jwt_auth.identify({'HTTP_AUTHORIZATION': ''}), is_(none()))

        assert_that(jwt_auth.identify({'HTTP_AUTHORIZATION': 'notbearer'}),
                    is_(none()))

    @time_monotonically_increases
    def test_max_age(self):
        max_age = _get_jwt_max_age({})
        assert_that(max_age, none())
        
        max_age = _get_jwt_max_age({'exp': 'aaa'})
        assert_that(max_age, none())
        
        # Negative
        max_age = _get_jwt_max_age({'exp': '60'})
        assert_that(max_age, is_('0'))
        
        now = round(time.time())
        max_age = _get_jwt_max_age({'exp': str(now + 3600)})
        assert_that(round(float(max_age)), is_(3599))
        
        # Admin defaults to 3600
        max_age = _get_jwt_max_age({'exp': str(now), 'admin': "true"})
        assert_that(max_age, is_('3600'))
        

    @WithMockDSTrans
    def test_identify_jwt_token(self):
        jwt_auth = DataserverJWTAuthenticator(secret='jwt_secret')
        def get_environ(payload, secret='jwt_secret'):
            jwt_token = encode(payload, secret)
            return {'HTTP_AUTHORIZATION': 'Bearer %s' % jwt_token}

        def do_auth(payload, jwt_auth=jwt_auth, expect_valid=True):
            env = get_environ(payload)
            identity = jwt_auth.identify(env)
            if expect_valid:
                assert_that(identity, not_none())
                return jwt_auth.authenticate(env, identity)
            else:
                assert_that(identity, none())
                return identity

        def is_admin(user):
            dataserver = component.getUtility(IDataserver)
            ds_folder = dataserver.root_folder['dataserver2']
            dsm = IPrincipalRoleManager(ds_folder)
            roles = dsm.getRolesForPrincipal(user.username)
            result = False
            if roles:
                result = (ROLE_ADMIN.id, Allow) in roles
            return result

        environ = get_environ({}, 'bad_secret')
        assert_that(jwt_auth.identify(environ), none())

        # We require the token's audience match our current site
        # Our current site is the root site dataserver2
        audience = 'dataserver2'
        
        # No user
        payload = {'login': 'no_user', 'aud': audience}
        assert_that(do_auth(payload), none())

        # Create
        payload = {'login': 'jwt_user', 'create': "true", 'aud': audience}
        assert_that(do_auth(payload), is_('jwt_user'))

        user = User.get_user('jwt_user')
        assert_that(user, not_none())
        assert_that(is_admin(user), is_(False))
        assert_that(IUserProfile(user).email, none())

        # Create admin with email
        payload = {'login': 'jwt_user_admin@nextthought.com',
                   'realname': 'jwt admin',
                   'email': 'jwtadmin@nextthought.com',
                   'admin': 'true',
                   'exp': time.time() + 300,
                   'create': "true",
                   'aud': audience}
        assert_that(do_auth(payload), is_('jwt_user_admin@nextthought.com'))
        
        env = get_environ(payload)
        jwt_id = jwt_auth.identify(env)
        # Admin defaults to one hour
        assert_that(jwt_id, has_entry('max_age', '3600'))

        user = User.get_user('jwt_user_admin@nextthought.com')
        assert_that(user, not_none())
        assert_that(is_admin(user), is_(True))
        assert_that(IUserProfile(user).email, is_('jwtadmin@nextthought.com'))
        assert_that(IUserProfile(user).realname, is_('jwt admin'))

        # Audience is required
        del payload['aud']
        assert_that(do_auth(payload, expect_valid=False), none())

        # But if there is an audience we reject if it doesn't match.
        payload['aud'] = 'different site'
        assert_that(do_auth(payload, expect_valid=False), none())

        # Issuer
        jwt_auth = DataserverJWTAuthenticator(secret='jwt_secret',
                                              issuer='nti_issuer')
        payload = {'login': 'jwt_user_admin_iss@nextthought.com',
                   'realname': 'jwt admin',
                   'email': 'jwtadmin@nextthought.com',
                   'admin': 'true',
                   'create': "true",
                   'iss': "bad_issuer",
                   'aud': audience}
        env = get_environ(payload)
        assert_that(jwt_auth.identify(env), none())
        payload['iss'] = 'nti_issuer'
        assert_that(do_auth(payload), is_('jwt_user_admin_iss@nextthought.com'))
