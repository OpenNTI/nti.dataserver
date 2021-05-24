#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import fudge

from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import is_
from hamcrest import same_instance

from nti.app.testing.request_response import DummyRequest

import unittest

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator


class _Decorator(AbstractAuthenticatedRequestAwareDecorator):

    def _do_decorate_external(self, context, request):
        pass

class TestAuthenticatedRequestAwareDecorator(unittest.TestCase):

    @fudge.patch('nti.app.renderers.decorators.get_remote_user')
    def test_remote_user_caches(self, mock_get_remote_user):

        class MockRemoteUser(object):
            pass

        request = DummyRequest()
        decorator = _Decorator(None, request)

        user = MockRemoteUser()
        mock_get_remote_user.is_callable().times_called(1).returns(user)

        assert_that(decorator.remoteUser, is_(same_instance(user)))
        assert_that(request, has_property('_v_AbstractAuthenticatedRequestAwareDecorator_remoteUser',
                                          same_instance(user)))

        # A new decorator in the same request uses the cached values
        another_decorator = _Decorator(None, request)
        assert_that(another_decorator.remoteUser, is_(same_instance(user)))
