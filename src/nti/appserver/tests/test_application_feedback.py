#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import  is_
from hamcrest import contains_string
from hamcrest import has_length
from hamcrest.library import has_property
from hamcrest import contains

from zope import interface
from zope import component

from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver import users
from nti.appserver import site_policies
from nti.appserver.feedback_views import REL_SEND_FEEDBACK

from nti.dataserver.tests import mock_dataserver
from nti.tests import is_empty

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS
from . import ITestMailDelivery


class TestApplicationFeedback(SharedApplicationTestBase):

	extra_environ_default_user = 'ossmkitty'

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_post_feedback_sends_email(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			coppa_user = users.User.get_user( self.extra_environ_default_user )
			interface.alsoProvides( coppa_user, site_policies.IMathcountsCoppaUserWithoutAgreement )
			user_interfaces.IFriendlyNamed( coppa_user ).realname = u'Jason'

		testapp = self.testapp
		mailer = component.getUtility( ITestMailDelivery )
		href = self.require_link_href_with_rel( self.resolve_user(), REL_SEND_FEEDBACK )
		assert_that( href, is_('/dataserver2/users/ossmkitty/@@send-feedback') )

		data = {'body': 'Hi there. I love it. This is a string that is long enough to make the wrapping kick in.'
				' It must be more than 60 or seventy characters.'}

		res = testapp.post_json( href, data )
		assert_that( res, has_property( 'status_int', 204 ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer, has_property( 'queue', has_length( 1 ) ) )
		assert_that( mailer, has_property( 'queue', contains( has_property( 'subject', "Feedback from ossmkitty" ) ) ) )

		assert_that( mailer.queue[0].as_string(), contains_string( "Hi there. I love it." ) )

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
