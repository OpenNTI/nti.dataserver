#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property
from hamcrest import contains_string
from hamcrest import contains


import anyjson as json
from zope import interface
from zope import component
from zope.component import eventtesting
from webtest import TestApp



from nti.dataserver.users import interfaces as user_interfaces
from nti.appserver import site_policies

from nti.dataserver.tests import mock_dataserver

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS
from . import ITestMailDelivery


class TestApplicationFeedback(SharedApplicationTestBase):


	@WithSharedApplicationMockDS
	def test_post_feedback_sends_email(self):
		component.provideHandler( eventtesting.events.append, (None,) )
		with mock_dataserver.mock_db_trans( self.ds ):
			coppa_user = self._create_user( username='ossmkitty' )
			interface.alsoProvides( coppa_user, site_policies.IMathcountsCoppaUserWithoutAgreement )
			user_interfaces.IFriendlyNamed( coppa_user ).realname = u'Jason'

		testapp = TestApp( self.app )
		mailer = component.getUtility( ITestMailDelivery )

		path = b'/dataserver2/users/ossmkitty/@@send-feedback'
		data = {'body': 'Hi there. I love it.'}

		res = testapp.post( path, json.dumps( data ), extra_environ=self._make_extra_environ(username='ossmkitty') )
		assert_that( res, has_property( 'status_int', 204 ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer, has_property( 'queue', has_length( 1 ) ) )
		assert_that( mailer, has_property( 'queue', contains( has_property( 'subject', "Feedback from ossmkitty" ) ) ) )

		assert_that( mailer.queue[0].as_string(), contains_string( "Hi there. I love it." ) )
