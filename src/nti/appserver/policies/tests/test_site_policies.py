#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
import fudge


from nti.app.testing.request_response import DummyRequest

from ..site_policies import guess_site_display_name


class TestGuessSiteDisplayName(unittest.TestCase):

	def test_no_request(self):
		assert_that(guess_site_display_name(), is_("Unknown") )

	def test_fallback_to_host(self):

		request = DummyRequest.blank(b'/foo/bar/site.js')
		request.host = 'janux.nextthought.com'

		assert_that( guess_site_display_name(request), is_('Janux'))

		request.host = 'ou-alpha.nextthought.com'
		assert_that( guess_site_display_name(request), is_('Ou Alpha') )


		request.host = 'localhost:80'
		assert_that( guess_site_display_name(request), is_('Localhost') )

	@fudge.patch('nti.appserver.policies.site_policies.find_site_policy')
	def test_with_display_name(self, mock_find):
		class Policy(object):
			DISPLAY_NAME = 'Janux'
		mock_find.is_callable().returns( (Policy, None) )

		assert_that( guess_site_display_name(), is_('Janux') )


	@fudge.patch('nti.appserver.policies.site_policies.find_site_policy')
	def test_with_policy_no_display_name_no_request(self, mock_find):
		class Policy(object):
			pass
		mock_find.is_callable().returns( (Policy, None) )

		assert_that( guess_site_display_name(), is_('Unknown') )

	@fudge.patch('nti.appserver.policies.site_policies.find_site_policy')
	def test_with_policy_no_display_name_site_name(self, mock_find):
		class Policy(object):
			pass
		mock_find.is_callable().returns( (Policy, 'prmia.nextthought.com') )

		assert_that( guess_site_display_name(), is_('Prmia') )
