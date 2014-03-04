#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import is_not as does_not

from nti.testing.matchers import validly_provides

from ..who_basicauth import ApplicationBasicAuthPlugin
from repoze.who.interfaces import IChallenger

class TestBasicAuth(unittest.TestCase):
	def test_non_challenging_challenge(self):

		challenger = ApplicationBasicAuthPlugin('nti')
		assert_that( challenger, validly_provides(IChallenger) )

		# Challenging produces as 401, but without a WWW-Authenticate header
		unauth = challenger.challenge( {}, '401', {}, [] )
		assert_that( unauth.headers, does_not( has_key( 'WWW-Authenticate' ) ) )
		assert_that( unauth.headers, has_key( 'Content-Type' ) )

		# forgetting adds no headers
		assert_that( challenger.forget( {}, {} ), is_( () ) )
