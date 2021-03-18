#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import assert_that
from hamcrest import is_
from nti.app.authentication import user_can_login

from nti.app.authentication.tests import AuthenticationLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.users import User

logger = __import__('logging').getLogger(__name__)


class TestUserCanLogin(AuthenticationLayerTest):

    @WithMockDSTrans
    def test_non_ascii(self):
        # previously raised exceptions
        assert_that(user_can_login(u"Händel"), is_(False))

    @WithMockDSTrans
    def test_success(self):
        user = User.create_user(username=u"bugs.bunny")
        # previously raised exceptions
        assert_that(user_can_login(u"bugs.bunny"), is_(True))
