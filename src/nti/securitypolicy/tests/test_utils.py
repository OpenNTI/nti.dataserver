#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from hamcrest import assert_that
from hamcrest import is_

from nti.securitypolicy.utils import is_impersonating

class TestImpersonationCheck(unittest.TestCase):

	def _simulated_request(self, impersonationTarget=None):

		class _MockRequest(object):
			environ = None

		request = _MockRequest()
		request.environ = {'REMOTE_USER_DATA': impersonationTarget}
		return request

	def test_impersonated(self):
		request = self._simulated_request(impersonationTarget='huey@nt.com')
		assert_that(is_impersonating(request), is_(True))

	def test_not_impersonated(self):
		request = self._simulated_request()
		assert_that(is_impersonating(request), is_(False))