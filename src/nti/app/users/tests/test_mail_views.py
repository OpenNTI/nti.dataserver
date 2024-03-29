#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
import re

from hamcrest import is_
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import contains_string
from hamcrest import matches_regexp

from six.moves import urllib_parse

from nti.app.users import VERIFY_USER_EMAIL_VIEW

from nti.app.users.utils import generate_legacy_mail_verification_pair
from nti.app.users.utils import generate_mail_verification_pair
from nti.app.users.utils import get_verification_signature_data
from nti.app.users.utils import generate_verification_email_url

from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import is_email_verified

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver


class TestMailViewFunctions(mock_dataserver.DataserverLayerTest):

    @mock_dataserver.WithMockDSTrans
    def test_generate_mail_verification_token(self):
        user = User.create_user(self.ds, username=u'ichigo',
                                password=u'temp001')

        IUserProfile(user).email = u"ichigo@bleach.org"

        signature, _ = generate_mail_verification_pair(user, None,
                                                       secret_key='zangetsu')
        legacy_signature, _ = \
            generate_legacy_mail_verification_pair(user, None,
                                                   secret_key='zangetsu')

        assert signature != legacy_signature
        # Since the payload is no longer a mapping, this applies only to legacy:
        # Note that we do not test the exact return values of signature and token.
        # They are dependent upon hash values, which may change from version
        # to version or impl to impl, or even run-to-run if the PYTHONHASHSEED
        # environment variable is set or the -R argument is given

        # However, we have only observed two permutations, so we test both of those
        # in addition to what we got (any instance down the road needs to be able
        # to decode the signature)
        # default - 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6ImljaGlnbyIsImVtYWlsIjoiaWNoaWdvQGJsZWFjaC5vcmcifQ.xvJVEzsqnQwcpPncSxjd_6rah0W2-fjp7_ShTVqM6h_-XVjgusYgEs5i3g0osoUkqAp84lzZZJZDPObNnFGIdA'
        for sig in (signature,
                    'eyJhbGciOiJIUzUxMiJ9.W1sidXNlcm5hbWUiLCJpY2hpZ28iXSxbImVtYWlsIiwiaWNoaWdvQGJsZWFjaC5vcmciXV0.laTL2Y-nnx83dfh0XAp-ylmTQBAGzwZVJBqgkhuyGcDFV0ewoTeOtaGw6T1yzuSsK9DFuEzKQp3cSGzpE8Vmmg',
                    legacy_signature,
                    'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6ImljaGlnbyIsImVtYWlsIjoiaWNoaWdvQGJsZWFjaC5vcmcifQ.xvJVEzsqnQwcpPncSxjd_6rah0W2-fjp7_ShTVqM6h_-XVjgusYgEs5i3g0osoUkqAp84lzZZJZDPObNnFGIdA',
                    'eyJhbGciOiJIUzUxMiJ9.eyJlbWFpbCI6ImljaGlnb0BibGVhY2gub3JnIiwidXNlcm5hbWUiOiJpY2hpZ28ifQ.l8Us0zxJU-9keq9vIR2TIcICKBHjwTLoT_KZv6eK9jzBkvHx9DRpuDqlqiC-0cpClxfN9AS6OkmKVZ6At46pyg'):
            data = get_verification_signature_data(user, sig,
                                                   secret_key='zangetsu')
            assert_that(data, has_entry('username', is_('ichigo')))
            assert_that(data, has_entry('email', is_('ichigo@bleach.org')))


class TestMailViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_verify_user_email_with_token(self):
        self._check_verify_user_email_with_token(generate_mail_verification_pair)

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_verify_user_email_with_token_legacy(self):
        self._check_verify_user_email_with_token(generate_legacy_mail_verification_pair)

    def _check_verify_user_email_with_token(self, token_factory):
        email = username = u'ichigo@bleach.org'
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(username=username, password=u'temp001',
                                    external_value={u'email': email})

            _, token = token_factory(user)

        post_data = {'token': token}
        path = '/dataserver2/@@verify_user_email_with_token'
        extra_environ = self._make_extra_environ(user=username)
        self.testapp.post_json(path, post_data,
                               extra_environ=extra_environ, status=204)

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(username)
            assert_that(IUserProfile(user),
                        has_property('email_verified', is_(True)))
            assert_that(is_email_verified(email), is_(True))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_verify_user_email_view(self):
        self._check_verify_user_email_view(generate_verification_email_url)

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_verify_user_email_view_legacy(self):
        def url_factory(user):
            signature, token = generate_legacy_mail_verification_pair(user=user)
            params = urllib_parse.urlencode({'username': user.username.lower(),
                                             'signature': signature})

            href = '/dataserver2/%s?%s' % ('@@' + VERIFY_USER_EMAIL_VIEW, params)
            return href, token

        self._check_verify_user_email_view(url_factory)

    def _check_verify_user_email_view(self, url_factory):
        email = username = u'ichigo@bleach.org'
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(username=username, password=u'temp001',
                                    external_value={u'email': email})

            href, _, = url_factory(user)

        extra_environ = self._make_extra_environ(user=username)
        result = self.testapp.get(href, extra_environ=extra_environ,
                                  status=200)

        assert_that(result.body, contains_string('html'))
        assert_that(result.body, contains_string('Thank you!'))

        rex = re.compile(u"You will be redirected to.*NextThought.*in.*seconds",
                         re.DOTALL)
        assert_that(result.body, matches_regexp(rex))

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(username)
            assert_that(IUserProfile(user),
                        has_property('email_verified', is_(True)))
            assert_that(is_email_verified(email), is_(True))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_verify_user_email_invalid_view(self):
        email = username = u'ichigo@bleach.org'
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(username=username, password=u'temp001',
                                    external_value={u'email': email})

            href, _, = generate_verification_email_url(user)

        # Our default user cannot validate someone else
        result = self.testapp.get(href, status=200)
        assert_that(result.body, contains_string('html'))
        assert_that(result.body, contains_string("We're Sorry."))

        # Munge the signature such that the verification fails
        # We only validate the signature, so mangle that.
        href = href.replace('signature=', 'signature=baddata')

        extra_environ = self._make_extra_environ(user=username)
        result = self.testapp.get(href, extra_environ=extra_environ,
                                  status=200)

        assert_that(result.body, contains_string('html'))
        assert_that(result.body, contains_string("We're Sorry."))

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(username)
            assert_that(IUserProfile(user),
                        has_property('email_verified', is_(None)))
            assert_that(is_email_verified(email), is_(False))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_email_verification_link(self):
        username = u'ichigo'
        with mock_dataserver.mock_db_trans(self.ds):
            User.create_user(username=username, password=u'temp001',
                             external_value={u'email': u"ichigo@bleach.org"})

        extra_environ = self._make_extra_environ(user=username)
        path = '/dataserver2/users/ichigo'
        res = self.testapp.get(path, extra_environ=extra_environ, status=200)
        assert_that(res.json_body,
                    has_entries('Links', has_item(has_entry('rel', 'RequestEmailVerification'))))
        assert_that(res.json_body,
                    has_entries('Links', has_item(has_entry('rel', 'VerifyEmailWithToken'))))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_request_email_verification(self):
        username = u'ichigo'
        with mock_dataserver.mock_db_trans(self.ds):
            User.create_user(username=username, password='temp001',
                             external_value={u'email': u"ichigo@bleach.org"})

        extra_environ = self._make_extra_environ(user=username)
        href = '/dataserver2/users/ichigo/@@request_email_verification'
        self.testapp.post(href, extra_environ=extra_environ, status=204)
        self.testapp.post(href, extra_environ=extra_environ, status=422)
