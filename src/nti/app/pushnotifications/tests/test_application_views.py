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

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_property


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
		self._fetch_user_url('/@@unsubscribe_digest_email')

		# Our pref is now false.
		res = self._fetch_user_url( '/++preferences++' )
		assert_that( res.json_body['PushNotifications']['Email'],
					 has_entry('email_a_summary_of_interesting_changes', False) )

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=False)
	def test_unsubscribe_unauthenticated(self):
		# Pretend to be a browser so we get redirected
		extra_environ = {'nti.paste.testing.classification': 'browser'}
		redir_res = self.testapp.get('/dataserver2/@@unsubscribe_digest_email', extra_environ=extra_environ)

		assert_that( redir_res,
					 has_property( 'location',
								   'http://localhost/login/?return=http%3A%2F%2Flocalhost%3A80%2Fdataserver2%2F%2540%2540unsubscribe_digest_email'))

		# Supply authentication now
		self.testapp.get('/dataserver2/@@unsubscribe_digest_email', status=200, extra_environ=self._make_extra_environ())

		# Our pref is now false.
		res = self._fetch_user_url( '/++preferences++', status=200, extra_environ=self._make_extra_environ() )
		assert_that( res.json_body['PushNotifications']['Email'],
					 has_entry('email_a_summary_of_interesting_changes', False) )
