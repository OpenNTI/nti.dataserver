#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import assert_that

import unittest

from nti.securitypolicy.utils import is_impersonating


class TestImpersonationCheck(unittest.TestCase):

    def _simulated_request(self, impersonationTarget=None):

        class _MockRequest(object):
            environ = None

        userdata = {'username': impersonationTarget}
        identity = {'userdata': userdata}

        request = _MockRequest()
        request.environ = {'repoze.who.identity': identity}
        return request

    def test_impersonated(self):
        request = self._simulated_request(impersonationTarget=u'huey@nt.com')
        assert_that(is_impersonating(request), is_(True))

    def test_not_impersonated(self):
        request = self._simulated_request()
        assert_that(is_impersonating(request), is_(False))
