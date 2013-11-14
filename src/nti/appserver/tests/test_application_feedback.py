#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import contains_string
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest.library import has_property
from hamcrest import contains
from hamcrest import is_not as does_not

from quopri import decodestring

from zope import component

from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver import users
from nti.appserver.feedback_views import REL_SEND_FEEDBACK

from nti.dataserver.tests import mock_dataserver
from nti.testing.matchers import is_empty

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS
from . import ITestMailDelivery


class TestApplicationFeedback(SharedApplicationTestBase):

	extra_environ_default_user = 'ossmkitty'

	def _do_test_email(self, url, subject, message_key, extra_data=None):
		with mock_dataserver.mock_db_trans( self.ds ):
			coppa_user = users.User.get_user( self.extra_environ_default_user )
			user_interfaces.IFriendlyNamed( coppa_user ).realname = u'Jason'

		testapp = self.testapp
		mailer = component.getUtility( ITestMailDelivery )

		data = {message_key: 'Hi there. I love it. This is a string that is long enough to make the wrapping kick in.'
				' It must be more than 60 or seventy characters.',
		}
		if extra_data:
			data.update(extra_data)

		res = testapp.post_json( url, data )
		assert_that( res, has_property( 'status_int', 204 ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer, has_property( 'queue', has_length( 1 ) ) )
		assert_that( mailer, has_property( 'queue', contains( has_property( 'subject', subject ) ) ) )

		assert_that( decodestring(mailer.queue[0].as_string()), contains_string( "Hi there. I love it." ) )
		return mailer.queue[0]


	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_post_feedback_sends_email(self):
		url = '/dataserver2/users/ossmkitty/@@send-feedback'
		self._do_test_email(url, 'Feedback From ossmkitty', 'body')

		href = self.require_link_href_with_rel( self.resolve_user(), REL_SEND_FEEDBACK )
		assert_that( href, is_(url) )


	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_post_bad_feedback(self):
		testapp = self.testapp
		user = self.resolve_user( )

		href = self.require_link_href_with_rel( user, REL_SEND_FEEDBACK )
		assert_that( href, is_('/dataserver2/users/ossmkitty/@@send-feedback') )


		mailer = component.getUtility( ITestMailDelivery )

		for body in (None, '', '   '):
			data = {'body': body}

			testapp.post_json( href,
							   data,
							   status=400 )
			mailer = component.getUtility( ITestMailDelivery )
			assert_that( mailer, has_property( 'queue', is_empty() ) )

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_post_crash_sends_email(self):
		url = '/dataserver2/@@send-crash-report'
		msg = self._do_test_email(url, 'Crash Report From ossmkitty', 'message',
								  {'file': 'thing.js', 'line': 82 })

		assert_that( decodestring(msg.as_string()),
					 contains_string( "    file          u'thing.js'" ) )

		assert_that( decodestring(msg.as_string()),
					 does_not( contains_string('HTTP_COOKIE')))

		assert_that( msg, has_entry( 'To', 'crash.reports@nextthought.com'))
