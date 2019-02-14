#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,no-member,too-many-public-methods

from hamcrest import is_
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that

from zope import interface

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.users import User

from nti.dataserver.users.tokens import UserToken


class TestTokensViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=(u'user001', u'user002', u'test001@nextthought.com'), testapp=True, default_authenticate=False)
    def test_user_tokens_view(self):
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(u'user001')
            container = IUserTokenContainer(user)

            token = UserToken(title=u'token1',
                              description=u'token1 desc',
                              scopes=(u'one',),
                              expiration_date=None)
            container.store_token(token)
            assert_that(container.tokens, has_length(1))

        # Read all
        url = '/dataserver2/users/user001'
        result = self.testapp.get(url, status=200, extra_environ=self._make_extra_environ(username=u'user001')).json_body
        url = self.require_link_href_with_rel(result, 'tokens')
        assert_that(url, is_('/dataserver2/users/user001/tokens'))

        # Read all tokens.
        self.testapp.get(url, status=401, extra_environ=self._make_extra_environ(username=None))
        self.testapp.get(url, status=403, extra_environ=self._make_extra_environ(username=u'user002'))
        self.testapp.get(url, status=403, extra_environ=self._make_extra_environ(username=u'test001@nextthought.com'))
        result = self.testapp.get(url, status=200, extra_environ=self._make_extra_environ(username=u'user001')).json_body
        assert_that(result, has_entries({'Total': 1,
                                         'ItemCount': 1,
                                         'Items': has_length(1)}))

        # Read single
        ntiid = result['Items'][0]['NTIID']
        url = '%s/%s' % (url, ntiid)

        self.testapp.get(url, status=401, extra_environ=self._make_extra_environ(username=None))
        self.testapp.get(url, status=403, extra_environ=self._make_extra_environ(username=u'user002'))
        self.testapp.get(url, status=403, extra_environ=self._make_extra_environ(username=u'test001@nextthought.com'))
        result = self.testapp.get(url, status=200, extra_environ=self._make_extra_environ(username=u'user001')).json_body
        assert_that(result, has_entries({'NTIID': ntiid}))

    def _assert_token_container(self, username='user001', length=0):
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(username)
            container = IUserTokenContainer(user)
            assert_that(container.tokens, has_length(length))

    @WithSharedApplicationMockDS(users=(u'user001', u'user002', u'test001@nextthought.com'), testapp=True, default_authenticate=False)
    def test_user_token_creation_and_deletion_view(self):
        ext_obj = {
            'token': "xxxx",
            'title': 'abc',
            'description': 'you',
            'scopes': [u'one', u'two'],
            'expiration_date': u'2019-02-12T00:00:00Z',
            'MimeType': 'application/vnd.nextthought.usertoken'
        }
        url = '/dataserver2/users/user001/tokens'
        self.testapp.post_json(url, ext_obj, status=401, extra_environ=self._make_extra_environ(username=None))
        self.testapp.post_json(url, ext_obj, status=403, extra_environ=self._make_extra_environ(username=u'user002'))
        self.testapp.post_json(url, ext_obj, status=403, extra_environ=self._make_extra_environ(username=u'test001@nextthought.com'))
        result = self.testapp.post_json(url, ext_obj, status=201, extra_environ=self._make_extra_environ(username=u'user001')).json_body
        assert_that(result['token'], is_not('xxxx'))
        assert_that(result, has_entries({'token': not_none(),
                                         'title': 'abc',
                                         'description': 'you',
                                         'scopes': contains('one', 'two'),
                                         'expiration_date': is_('2019-02-12T00:00:00Z'),
                                         'MimeType': 'application/vnd.nextthought.usertoken'}))

        ext_obj['token'] = None
        ext_obj['title'] = u'xyz'
        result = self.testapp.post_json(url, ext_obj, status=201, extra_environ=self._make_extra_environ(username=u'user001')).json_body
        assert_that(result, has_entries({'token': not_none(),
                                         'title': 'xyz',
                                         'MimeType': 'application/vnd.nextthought.usertoken'}))

        self._assert_token_container(u'user001', 2)

        # delete all
        self.testapp.delete(url, status=401, extra_environ=self._make_extra_environ(username=None))
        self.testapp.delete(url, status=403, extra_environ=self._make_extra_environ(username=u'user002'))
        self.testapp.delete(url, status=403, extra_environ=self._make_extra_environ(username=u'test001@nextthought.com'))
        self.testapp.delete(url, status=204, extra_environ=self._make_extra_environ(username=u'user001'))

        self._assert_token_container(u'user001', 0)

        # delete single
        result = self.testapp.post_json(url, ext_obj, status=201, extra_environ=self._make_extra_environ(username=u'user001')).json_body

        self._assert_token_container(u'user001', 1)

        ntiid = result['NTIID']
        token_url = '%s/%s' % (url, ntiid)
        self.testapp.delete(token_url, status=401, extra_environ=self._make_extra_environ(username=None))
        self.testapp.delete(token_url, status=403, extra_environ=self._make_extra_environ(username=u'user002'))
        self.testapp.delete(token_url, status=204, extra_environ=self._make_extra_environ(username=u'user001'))
        self.testapp.delete(token_url, status=404, extra_environ=self._make_extra_environ(username=u'user001'))

        self.testapp.get(token_url, status=404, extra_environ=self._make_extra_environ(username=u'user001'))
        self._assert_token_container(u'user001', 0)
