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
from hamcrest import has_entry


from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

class TestUnsubscribe(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_unsubscribe(self):
		# First, be sure we're True
		res = self._fetch_user_url( '/++preferences++' )
		assert_that( res.json_body['PushNotifications']['Email'],
					 has_entry('email_a_summary_of_interesting_changes', True) )


		# Now unsubscribe. Note that we're doing direct authentication,
		# not token-based
		self._fetch_user_url('/unsubscribe')

		# Our pref is now false.
		res = self._fetch_user_url( '/++preferences++' )
		assert_that( res.json_body['PushNotifications']['Email'],
					 has_entry('email_a_summary_of_interesting_changes', False) )
