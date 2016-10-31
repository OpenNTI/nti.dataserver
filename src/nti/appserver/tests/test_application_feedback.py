#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string
from hamcrest import is_not as does_not

from nti.testing.matchers import is_empty

from quopri import decodestring

from zope import component

from nti.appserver.feedback_views import REL_SEND_FEEDBACK

from nti.dataserver import users

from nti.dataserver.users import interfaces as user_interfaces

from nti.appserver.tests import ITestMailDelivery

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

class TestApplicationFeedback(ApplicationLayerTest):

	extra_environ_default_user = 'ossmkitty'

	def _do_test_email(self, url, subject, message_key, extra_data=None, extra_environ=None):

		with mock_dataserver.mock_db_trans(self.ds):
			coppa_user = users.User.get_user(self.extra_environ_default_user)
			user_interfaces.IFriendlyNamed(coppa_user).realname = u'Jason'

		testapp = self.testapp
		data = {
			message_key: 'Hi there. I love it. This is a string that is long enough to make the wrapping kick in.'
			' It must be more than 60 or seventy characters.',
		}
		if extra_data:
			data.update(extra_data)

		res = testapp.post_json(url, data, extra_environ=extra_environ)
		assert_that(res, has_property('status_int', 204))

		mailer = component.getUtility(ITestMailDelivery)
		assert_that(mailer, has_property('queue', has_length(1)))
		assert_that(mailer, has_property('queue', contains(has_property('subject', subject))))

		assert_that(decodestring(mailer.queue[0].as_string()), contains_string(b"Hi there. I love it."))
		return mailer.queue[0]

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_post_feedback_sends_email_funky_char(self):
		url = '/dataserver2/users/ossmkitty/@@send-feedback'
		# The layers of JSON and decoding make it hard to get a bad byte in the
		# body data, but we can directly but one in the environ
		self._do_test_email(url, 'Feedback From ossmkitty on localhost', 'body',
							extra_environ={'nti.testing.bad_data': b'Exotic char: \xe2'})

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_post_feedback_sends_email(self):
		url = '/dataserver2/users/ossmkitty/@@send-feedback'
		self._do_test_email(url, 'Feedback From ossmkitty on localhost', 'body')

		href = self.require_link_href_with_rel(self.resolve_user(), REL_SEND_FEEDBACK)
		assert_that(href, is_(url))


	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_post_bad_feedback(self):
		testapp = self.testapp
		user = self.resolve_user()

		href = self.require_link_href_with_rel(user, REL_SEND_FEEDBACK)
		assert_that(href, is_('/dataserver2/users/ossmkitty/@@send-feedback'))

		mailer = component.getUtility(ITestMailDelivery)

		for body in (None, '', '   '):
			data = {'body': body}

			testapp.post_json(href,
							   data,
							   status=400)
			mailer = component.getUtility(ITestMailDelivery)
			assert_that(mailer, has_property('queue', is_empty()))

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_post_crash_sends_email(self):
		url = '/dataserver2/@@send-crash-report'
		msg = self._do_test_email(url, 'Crash Report From ossmkitty on localhost', 'message',
								  {'file': 'thing.js', 'line': 82,
								   'collectedLog': ['an', 'array', 'of', 'strings',
													'that sometimes', 'can get to be',
													'really long',
													'and have exotic chars: \xe2'],
								   'stacktrace': {'sometimes': 'comes in', 'as a': 'dict'}})

		msg_string = decodestring(msg.as_string())
		assert_that(msg_string,
					contains_string(b"file"))
		assert_that(msg_string,
					contains_string(b"thing.js"))
		assert_that(msg_string,
					 contains_string(b"collectedLog"))
		assert_that(msg_string,
					contains_string(b"['an',\n"))
		assert_that(msg_string,
					 contains_string(b"greenlet.GreenletExit"))
		assert_that(msg_string,
					 does_not(contains_string(b'HTTP_COOKIE')))

		assert_that(msg, has_entry('To', 'crash.reports@nextthought.com'))

	@WithSharedApplicationMockDS(testapp=True,
								 users=('sjohnson@nextthought.com', 'nobody@nowhere.com'),
								 default_authenticate=False)
	def test_post_crash_sends_email_impersonated(self):
		url = '/dataserver2/@@send-crash-report'
		# Setup an impersonated session
		testapp = self.testapp
		testapp.get('/dataserver2/logon.nti.impersonate', params={'username': 'nobody@nowhere.com'},
					extra_environ=self._make_extra_environ('sjohnson@nextthought.com'))

		# In order for the domain-specific cookie we just set to get back
		# to the server, we must switch out the policy
		from cookielib import DefaultCookiePolicy
		class Policy(DefaultCookiePolicy):

			def set_ok(self, *args):
				return True

			def return_ok(self, *args):
				return True
		testapp.cookiejar.set_policy(Policy())

		msg = self._do_test_email(url, 'Crash Report From nobody@nowhere.com on localhost', 'message',
								  {'file': 'thing.js', 'line': 82 })

		# XXX: Sometimes we get UnicodeDecodeErrors here if we let the literal
		# be unicode. It seems that either the mail library is incorrectly producing
		# quoted printable text, or the quopri is incorrectly decoding such text;
		# given a string like:
		#	Content-Type: multipart/alternative;\n boundary="===============9118329845803160203==
		# the decoded value becomes:
		#	Content-Type: multipart/alternative;\n boundary="=======\x9118329845803160203=
		# Note the incorrect (?) transformation of the boundary.
		# Our solution here, and above, is to ensure the literal we compare with is
		# a bytestring.
		# XXX: Py3

		decoded = decodestring(msg.as_string())
		assert_that(decoded, contains_string(b"REMOTE_USER_DATA"))
		assert_that(decoded, contains_string(b"username=sjohnson%40nextthought.com"))
