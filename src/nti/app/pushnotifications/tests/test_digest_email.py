#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from zope import interface

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not as does_not
from hamcrest import has_key
from hamcrest import contains_string

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS


from nti.dataserver import users
from nti.dataserver import contenttypes
from nti.contentrange import contentrange
from nti.ntiids import ntiids
from nti.externalization.oids import to_external_ntiid_oid

from nti.externalization.internalization import update_from_external_object

from nti.dataserver.tests import mock_dataserver

from nti.testing.time import time_monotonically_increases
from nti.testing.matchers import is_true

from nti.app.bulkemail import views as bulk_email_views

import fudge
import gevent


SEND_QUOTA = {u'GetSendQuotaResponse': {u'GetSendQuotaResult': {u'Max24HourSend': u'50000.0',
																u'MaxSendRate': u'14.0',
																u'SentLast24Hours': u'195.0'},
										u'ResponseMetadata': {u'RequestId': u'232fb429-b540-11e3-ac39-9575ac162f26'}}}


class TestApplicationDigest(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True,testapp=True)
	@fudge.patch('boto.ses.connect_to_region')
	def test_application_get(self, fake_connect):
		(fake_connect.is_callable().returns_fake())
		 #.expects( 'send_raw_email' ).returns( 'return' )
		 #.expects('get_send_quota').returns( SEND_QUOTA ))
		# Initial condition
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
		assert_that( res.body, contains_string( 'Start' ) )

		res = res.form.submit( name='subFormTable.buttons.start' ).follow()
		assert_that( res.body, contains_string( 'Remaining' ) )

	def _create_notable_data(self):
		# Create a notable blog
		res = self.testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog',
									  {'Class': 'Post', 'title': 'my title', 'body': ['my body']},
									  status=201 )
		# Sharing is currently a two-step process
		self.testapp.put_json(res.json_body['href'], {'sharedWith': ['jason']})


		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			jason = self._get_user('jason')
			# And a couple notable notes
			for i in range(5):
				top_n = contenttypes.Note()
				top_n.applicableRange = contentrange.ContentRangeDescription()
				top_n.containerId = u'tag:nti:foo'
				top_n.body = ("Top is notable", str(i))
				top_n.createdTime = 100 + i
				top_n.creator = user
				top_n.tags = contenttypes.Note.tags.fromObject([jason.NTIID])
				top_n.addSharingTarget(jason)
				user.addContainedObject( top_n )

			# A circled event
			jason.accept_shared_data_from(user)

			# make sure he has an email
			from nti.dataserver.users import interfaces as user_interfaces
			from zope.lifecycleevent import modified

			user_interfaces.IUserProfile( jason ).email = 'jason.madden@nextthought.com'
			modified( jason )


	@WithSharedApplicationMockDS(users=('jason',), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto.ses.connect_to_region')
	def test_with_notable_data(self, fake_connect):
		def check_send(*args):
			return 'return'

		(fake_connect.is_callable().returns_fake()
		 .expects( 'send_raw_email' ).calls(check_send)
		 .expects('get_send_quota').returns( SEND_QUOTA ))

		self._create_notable_data()

		# Kick the process
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
		assert_that( res.body, contains_string( 'Start' ) )

		res = res.form.submit( name='subFormTable.buttons.start' ).follow()
		assert_that( res.body, contains_string( 'Remaining' ) )

		# Let the spawned greenlet do its thing
		gevent.joinall(bulk_email_views._BulkEmailView._greenlets)
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
		assert_that( res.body, contains_string( 'End Time' ) )


	@WithSharedApplicationMockDS(users=('jason',), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	@fudge.patch('boto.ses.connect_to_region')
	def test_with_notable_data_but_unsubscribed(self, fake_connect):
		def check_send(*args):
			raise AssertionError("This should not be called")

		(fake_connect.is_callable().returns_fake()
		 .provides( 'send_raw_email' ).calls(check_send)
		 .expects('get_send_quota').returns( SEND_QUOTA ))

		self._create_notable_data()

		self._fetch_user_url('/unsubscribe',
							 username='jason',
							 extra_environ=self._make_extra_environ(username='jason'))
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
		assert_that( res.body, contains_string( 'Start' ) )

		res = res.form.submit( name='subFormTable.buttons.start' ).follow()
		assert_that( res.body, contains_string( 'Remaining' ) )

		# Let the spawned greenlet do its thing
		gevent.joinall(bulk_email_views._BulkEmailView._greenlets)
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/digest_email' )
		assert_that( res.body, contains_string( 'End Time' ) )
