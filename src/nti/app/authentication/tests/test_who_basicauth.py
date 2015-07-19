#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_key
from hamcrest import equal_to
from hamcrest import assert_that
from hamcrest import is_not as does_not

import unittest

from repoze.who.interfaces import IChallenger

from nti.app.authentication.who_basicauth import ApplicationBasicAuthPlugin

from nti.testing.matchers import validly_provides

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
