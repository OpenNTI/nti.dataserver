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
from hamcrest import is_not as does_not
from hamcrest import has_property
from hamcrest import has_items
from hamcrest import none
from hamcrest import not_none

from nti.testing.time import time_monotonically_increases
import fudge

from pyramid.request import Request
from pyramid.security import Authenticated
from pyramid.security import Everyone

from ..who_policy import AuthenticationPolicy
from ..who_apifactory import create_who_apifactory
from ..who_authenticators import ANONYMOUS_USERNAME

from zope.authentication import interfaces

class TestWhoPolicy(unittest.TestCase):

	def setUp(self):
		self.api_factory = create_who_apifactory()
		self.policy = AuthenticationPolicy(self.api_factory.default_identifier_name,
									  api_factory=self.api_factory)

	@time_monotonically_increases
	def test_reissue(self, ):
		mock_get = fudge.Fake()
		mock_get.is_callable().returns({'login_app_root': '/login'})
		with fudge.patched_context('zope.component', 'getUtility', mock_get):
			policy = self.policy

			request = Request.blank('/')
			headers = policy.remember(request, 'jason')

			request = Request.blank('/',
									{'HTTP_COOKIE': headers[0][1]})

			api = policy._getAPI(request)
			ident = api.name_registry[policy._identifier_id]
			ident.userid_checker = None
			assert_that( policy.unauthenticated_userid(request),
						 is_('jason'))

			assert_that( request, does_not(has_property('_authtkt_reissued')))


			ident.reissue_time = 1

			assert_that( policy.unauthenticated_userid(request),
						 is_('jason'))
			# Side-effect: need a reissue
			assert_that( request, has_property('_authtkt_reissued'))

	def test_allows_anonymous_for_tvos( self ):
		policy = self.policy

		request = Request.blank('/')
		assert_that(policy.unauthenticated_userid(request), none())

		request = Request.blank('/', headers={'User-Agent': b"NextThought/1.0.2 ntitvos CFNetwork/672.0.8 Darwin/13.0.0"})
		assert_that(policy.unauthenticated_userid(request), is_(ANONYMOUS_USERNAME))

	def test_anonymous_effective_principles( self ):
		unknown_principal = 'test_unauthed_principal_id'

		mock_get = fudge.Fake()
		mock_get.is_callable().returns( {} ).next_call().with_args( interfaces.IUnauthenticatedPrincipal ).returns( unknown_principal )
		with fudge.patched_context('zope.component', 'getUtility', mock_get):

			policy = self.policy
			request = Request.blank('/', headers={'User-Agent': b"NextThought/1.0.2 ntitvos CFNetwork/672.0.8 Darwin/13.0.0"})
			effective_principals = policy.effective_principals(request)
			
			assert_that(effective_principals, has_items(ANONYMOUS_USERNAME, unknown_principal, Everyone))
			assert_that(effective_principals, does_not(has_items(Authenticated)))
