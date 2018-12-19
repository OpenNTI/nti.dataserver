#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

import unittest

from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dataserver.users.tokens import UserToken

from nti.dataserver.users.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.externalization.externalization import to_external_object


class TestUserTokens(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_tokens(self):
        user = User.create_user(username='ichigo@bleach.org')
        container = IUserTokenContainer(user, None)
        assert_that(container, has_length(0))
        user_token = UserToken(title=u"title",
                               description=u"desc",
                               scopes=(u"user:scope",))
        assert_that(user_token, has_property('title', u'title'))
        assert_that(user_token, has_property('description', u'desc'))
        assert_that(user_token, has_property('scopes', contains(u'user:scope')))
        assert_that(user_token, has_property('token', none()))
        container.store_token(user_token)

        assert_that(user_token, has_property('token', not_none()))
        assert_that(container, has_length(1))

        assert_that(container.get_all_tokens_by_scope('dne:scope'), has_length(0))
        assert_that(container.get_all_tokens_by_scope('user:scope'), contains(user_token))

        user_token_ext = to_external_object(user_token)
        assert_that(user_token_ext, has_entry('title', u'title'))
        assert_that(user_token_ext, has_entry('description', u'desc'))
        assert_that(user_token_ext, has_entry('scopes', contains(u'user:scope')))
        assert_that(user_token_ext, has_entry('token', not_none()))
