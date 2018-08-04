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
from hamcrest import has_property

from hamcrest import calling
from hamcrest import raises

from .. import views as bulk_email_views
from ..process import SiteTransactedBulkEmailProcessLoop
from ..process import PreflightError
from ..process import _RedisProcessMetaData as _ProcessMetaData
from ..delegate import AbstractBulkEmailProcessDelegate

from zope.security.interfaces import IPrincipal
from nti.mailer.interfaces import IEmailAddressable

from boto.ses.exceptions import SESDailyQuotaExceededError
from boto.ses.exceptions import SESError

import time

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

import fudge
from fudge.inspector import arg

SEND_QUOTA = {u'GetSendQuotaResponse': {u'GetSendQuotaResult': {u'Max24HourSend': u'50000.0',
																u'MaxSendRate': u'14.0',
																u'SentLast24Hours': u'195.0'},
										u'ResponseMetadata': {u'RequestId': u'232fb429-b540-11e3-ac39-9575ac162f26'}}}

class Process(SiteTransactedBulkEmailProcessLoop,
			  AbstractBulkEmailProcessDelegate):
	template_name = "nti.appserver:templates/failed_username_recovery_email"
	__name__ = 'failed_username_recovery_email'
	def __init__(self, request):
		super(Process,self).__init__(request)
		self.delegate = self

	def compute_template_args_for_recipient(self, recipient):
		result = super(Process, self).compute_template_args_for_recipient(recipient)
		result['support_email'] = 'support_email'
		return result

@interface.implementer(IEmailAddressable,
					   IPrincipal)
class Recipient(object):

	email = 'foo@bar'
	id = 'jason'
	verp_from = '"NextThought" <no-reply+jason.VRjdUA@alerts.nextthought.com>'
	def __init__(self, email=None):
		if email:
			self.email = email

class TestBulkEmailProcess(ApplicationLayerTest):

	def setUp(self):
		super(TestBulkEmailProcess,self).setUp()
		bulk_email_views._BulkEmailView._test_make_process = lambda s: Process(s.request) if s.request.subpath[0] == 'failed_username_recovery_email' else None
		bulk_email_views._BulkEmailView._greenlets = []

	def tearDown(self):
		del bulk_email_views._BulkEmailView._test_make_process
		super(TestBulkEmailProcess,self).tearDown()

	@WithSharedApplicationMockDS
	def test_preflight(self):
		process = Process(self.beginRequest())

		# all clear
		process.preflight_process()

		process.redis.set( process.names.lock_name, 'val' )
		assert process.redis.exists( process.names.lock_name )
		assert_that( calling(process.preflight_process), raises(PreflightError) )

		# reset
		process.reset_process()
		process.preflight_process()

	@WithSharedApplicationMockDS
	def test_add_recipients(self):
		process = Process(self.beginRequest())

		# No email
		assert_that( calling(process.add_recipients).with_args([{}]), raises(ValueError))

		process.preflight_process()

		process.add_recipients( [{'email': 'foo@bar'}, {'email': 'biz@baz'}] )
		assert_that( process.redis.scard(process.names.source_name), is_( 2 ) )

	@WithSharedApplicationMockDS
	@fudge.patch('nti.mailer._verp._get_signer_secret')
	def test_process_one_recipient(self, fake_secret):
		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_sesconn = fudge.Fake()
		(fake_sesconn.expects( 'send_raw_email' )
		 	.with_args( arg.any(), Recipient.verp_from, Recipient.email )
			.returns( {'key': 'val'} ) )

		process.sesconn = fake_sesconn
		fake_secret.is_callable().returns('abc123')

		process.add_recipients( [{'email': Recipient()}] )

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )

		process.process_one_recipient()

		assert_that( process.redis.scard(process.names.source_name), is_( 0 ) )
		assert_that( process.redis.scard(process.names.dest_name), is_( 1 ) )

	@WithSharedApplicationMockDS
	@fudge.patch('nti.mailer._verp._get_signer_secret')
	def test_process_loop(self, fake_secret):

		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_sesconn = fudge.Fake()
		(fake_sesconn.expects( 'send_raw_email' )
		 	.with_args( arg.any(), Recipient.verp_from, Recipient.email )
			.returns( {'key': 'val'} ) )
		fake_sesconn.expects('get_send_quota').returns( SEND_QUOTA )
		process.sesconn = fake_sesconn
		fake_secret.is_callable().returns('abc123')

		process.add_recipients( [{'email': Recipient()}] )

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )
		assert_that( process.redis.scard(process.names.dest_name), is_( 0 ) )

		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 0 ) )
		assert_that( process.redis.scard(process.names.dest_name), is_( 1 ) )

		fresh_metadata = _ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', 'Completed' ) )


	@WithSharedApplicationMockDS
	@fudge.test
	def test_process_loop_quota_exceeded(self):

		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_sesconn = fudge.Fake()
		exc = SESDailyQuotaExceededError( "404", "Reason" )
		fake_sesconn.expects( 'send_raw_email' ).raises( exc )
		fake_sesconn.expects('get_send_quota').returns( SEND_QUOTA )
		process.sesconn = fake_sesconn

		process.add_recipients( [{'email': Recipient()}] )

		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )

		fresh_metadata = _ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', str(exc) ) )

	@WithSharedApplicationMockDS
	@fudge.test
	def test_process_loop_seserror(self):

		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_sesconn = fudge.Fake()
		exc = SESError( "404", "Reason" )
		fake_sesconn.expects( 'send_raw_email' ).raises( exc )
		fake_sesconn.expects('get_send_quota').returns( SEND_QUOTA )
		process.sesconn = fake_sesconn

		process.add_recipients([ {'email': Recipient()}] )

		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )
		assert_that( process.__dict__, does_not( has_key( 'sesconn' ) ) )

		fresh_metadata = _ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', str(exc) ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	@fudge.patch('boto.ses.connect_to_region')
	def test_application_get(self, fake_connect):
		(fake_connect.is_callable().returns_fake()
		 .expects( 'send_raw_email' ).returns( 'return' )
		 .expects('get_send_quota').returns( SEND_QUOTA ))
		# Initial condition
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/failed_username_recovery_email' )
		assert_that( res.body, contains_string( 'Start' ) )


		# With some recipients
		email = 'jason.madden@nextthought.com'
		process = Process(self.beginRequest())
		process.add_recipients( [{'email': Recipient(email)}] )
		process.metadata.startTime = time.time()
		process.metadata.save()

		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/failed_username_recovery_email' )
		assert_that( res.body, contains_string( 'Remaining' ) )

		# Submit the form asking it to resume; follow the resulting GET redirect
		res = res.form.submit( name='subFormTable.buttons.resume' ).follow()
		assert_that( res.body, contains_string( 'Remaining' ) )
		# Let the spawned greenlet do its thing
		bulk_email_views._BulkEmailView._greenlets[0].join()
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/failed_username_recovery_email' )
		assert_that( res.body, contains_string( 'End Time' ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_application_get_template_dne(self):
		# Initial condition
		self.testapp.get( '/dataserver2/@@bulk_email_admin/no_such_template', status=404 )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_application_get_no_path(self):
		self.testapp.get( '/dataserver2/@@bulk_email_admin/', status=404 )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	@fudge.patch('boto.ses.connect_to_region')
	def test_application_policy_change(self, fake_connect):
		(fake_connect.is_callable().returns_fake()
		 .expects( 'send_raw_email' ).returns( 'return' )
		 .expects('get_send_quota').returns( SEND_QUOTA ))

		# Initial condition
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/policy_change_email' )
		assert_that( res.body, contains_string( 'Start' ) )

		# Give us an email
		from nti.dataserver.tests import mock_dataserver
		with mock_dataserver.mock_db_trans(self.ds):
			from nti.dataserver import users
			from nti.dataserver.users import interfaces as user_interfaces
			from zope.lifecycleevent import modified
			user = users.User.get_user( self.extra_environ_default_user )
			user_interfaces.IUserProfile( user ).email = 'jason.madden@nextthought.com'
			modified( user )


		# Now, make it start and run itself, finding applicable recipients,
		# etc
		res = res.form.submit( name='subFormTable.buttons.start' ).follow()
		assert_that( res.body, contains_string( 'Remaining' ) )

		# Let the spawned greenlet do its thing
		bulk_email_views._BulkEmailView._greenlets[0].join()
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/policy_change_email' )
		assert_that( res.body, contains_string( 'End Time' ) )
