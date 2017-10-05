#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_key
from hamcrest import equal_to
from hamcrest import assert_that
from hamcrest import is_not as does_not

from nti.testing.matchers import validly_provides

import unittest

from repoze.who.interfaces import IChallenger

from nti.app.authentication.who_basicauth import ApplicationBasicAuthPlugin


class TestBasicAuth(unittest.TestCase):

    def test_non_challenging_challenge(self):

        challenger = ApplicationBasicAuthPlugin('nti')
        assert_that(challenger, validly_provides(IChallenger))

        # Challenging produces as 401, but without a WWW-Authenticate header
        unauth = challenger.challenge({}, '401', {}, [])
        assert_that(unauth.headers, does_not(has_key('WWW-Authenticate')))
        assert_that(unauth.headers, has_key('Content-Type'))

        # forgetting adds no headers
        result = challenger.forget({}, {})
        assert_that(result, is_(equal_to(())))
