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


import contextlib

from zope import component
from zope import interface

from botocore.exceptions import ClientError

import fudge

from fudge.inspector import arg

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

from nti.mailer._verp import formataddr

import time

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dataserver.tests import mock_dataserver


SEND_QUOTA = {u'Max24HourSend': 50000.0,
			  u'MaxSendRate': 14.0,
			  u'SentLast24Hours': 195.0}
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
		result['context'] = self
		return result

@interface.implementer(IEmailAddressable,
					   IPrincipal)
class Recipient(object):

	email = 'foo@bar'
	id = 'jason'
	verp_from = formataddr(('NextThought', 'no-reply+jason.UrcYWQ@alerts.nextthought.com'))
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

	def _test_process_one_recipient(self, fake_secret, expected_sender):
		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_client = fudge.Fake()
		(fake_client.expects( 'send_raw_email' )
		 .with_args( RawMessage=arg.any(),
					 Source=expected_sender,
					 Destinations=[Recipient.email] )
		 .returns( {'key': 'val'} ) )

		process.client = fake_client
		fake_secret.is_callable().returns('abc123')

		process.add_recipients( [{'email': Recipient()}] )

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )

		process.process_one_recipient()

		assert_that( process.redis.scard(process.names.source_name), is_( 0 ) )
		assert_that( process.redis.scard(process.names.dest_name), is_( 1 ) )

	@WithSharedApplicationMockDS
	@fudge.patch('nti.mailer._verp._get_signer_secret')
	def test_process_one_recipient_no_policy_sender(self, fake_secret):
		expected_sender = Recipient.verp_from
		with modified_bulk_email_sender_for_site(self.ds, "dataserver2", None):
			self._test_process_one_recipient(fake_secret, expected_sender)

	@WithSharedApplicationMockDS
	@fudge.patch('nti.mailer._verp._get_signer_secret')
	def test_process_one_recipient_policy_sender(self, fake_secret):
		"""
		Ensure we get our sender address from the policy
		"""
		expected_sender = "Bulk Sender <no-reply+jason.UrcYWQ@bulk.nti.com>"
		policy_sender = "Bulk Sender <no-reply@bulk.nti.com>"
		with modified_bulk_email_sender_for_site(self.ds, "dataserver2", policy_sender):
			self._test_process_one_recipient(fake_secret, expected_sender)

	@WithSharedApplicationMockDS
	@fudge.patch(
		'nti.mailer._verp._get_signer_secret',
		'nti.app.bulkemail.delegate.AbstractBulkEmailProcessDelegate._site_policy')
	def test_process_one_recipient_sender_fallback(
			self,
			fake_secret,
			site_policy_property):
		"""
		Check fallback for sender address when there's no policy
		"""
		site_policy_property.is_callable().returns(None)
		expected_sender = Recipient.verp_from
		policy_sender = "Bulk Sender <no-reply@bulk.nti.com>"
		with modified_bulk_email_sender_for_site(self.ds, "dataserver2", policy_sender):
			self._test_process_one_recipient(fake_secret, expected_sender)

	@WithSharedApplicationMockDS
	@fudge.patch('nti.mailer._verp._get_signer_secret')
	def test_process_loop(self, fake_secret):

		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_client = fudge.Fake()
		(fake_client.expects( 'send_raw_email' )
		 .with_args( RawMessage=arg.any(),
					 Source=Recipient.verp_from,
					 Destinations=[Recipient.email] )
			.returns( {'key': 'val'} ) )
		fake_client.expects('get_send_quota').returns( SEND_QUOTA )
		process.client = fake_client
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
	@fudge.patch('nti.mailer._verp._get_signer_secret')
	def test_fallback(self, fake_secret):

		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_client = fudge.Fake()
		(fake_client.expects( 'send_raw_email' )
		 .with_args( RawMessage=arg.any(),
					 Source=Recipient.verp_from,
					 Destinations=[Recipient.email] )
			.returns( {'key': 'val'} ) )
		err_response = {
			"Error": {
				"Code": "Throttling",
				"Message": "Daily message quota exceeded."
			}
		}
		exc = ClientError(err_response, "SendRawEmail")
		fake_client.expects('get_send_quota').raises(exc)
		err_response = {
			"Error": {
				"Code": "Throttling",
				"Message": "Rate exceeded"
			}
		}
		exc = ClientError(err_response, "SendRawEmail")
		fake_client.next_call().raises(exc)
		process.client = fake_client
		fake_secret.is_callable().returns('abc123')

		process.add_recipients( [{'email': Recipient()}] )

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )
		assert_that( process.redis.scard(process.names.dest_name), is_( 0 ) )

		# Expect unhandled ClientError during quota fetch
		assert_that(calling(process.process_loop), raises(ClientError))

		# Next call should use fallback
		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 0 ) )
		assert_that( process.redis.scard(process.names.dest_name), is_( 1 ) )

		fresh_metadata = _ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', 'Completed' ) )

	@WithSharedApplicationMockDS
	@fudge.test
	def test_process_loop_invalid_throttle_exc(self):

		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_client = fudge.Fake()
		err_response = {
			"Error": {
				"Code": "Throttling",
				"Message": "Invalid throttle message."
			}
		}
		exc = ClientError(err_response, "SendRawEmail")
		fake_client.expects( 'send_raw_email' ).raises( exc )
		fake_client.expects('get_send_quota').returns( SEND_QUOTA )
		process.client = fake_client

		process.add_recipients( [{'email': Recipient()}] )

		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )
		assert_that( process.__dict__, does_not( has_key( 'client' ) ) )

		fresh_metadata = _ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', str(exc) ) )

	@WithSharedApplicationMockDS
	@fudge.test
	def test_process_loop_quota_exceeded(self):

		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_client = fudge.Fake()
		err_response = {
			"Error": {
				"Code": "Throttling",
				"Message": "Daily message quota exceeded."
			}
		}
		exc = ClientError(err_response, "SendRawEmail")
		fake_client.expects( 'send_raw_email' ).raises( exc )
		fake_client.expects('get_send_quota').returns( SEND_QUOTA )
		process.client = fake_client

		process.add_recipients( [{'email': Recipient()}] )

		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )

		fresh_metadata = _ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', str(exc) ) )

	@WithSharedApplicationMockDS
	@fudge.test
	def test_process_loop_clienterror(self):

		process = Process(self.beginRequest())
		process.subject = 'Subject'
		fake_client = fudge.Fake()
		exc = ClientError({}, "SendRawEmail" )
		fake_client.expects( 'send_raw_email' ).raises( exc )
		fake_client.expects('get_send_quota').returns( SEND_QUOTA )
		process.client = fake_client

		process.add_recipients([ {'email': Recipient()}] )

		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )
		assert_that( process.__dict__, does_not( has_key( 'client' ) ) )

		fresh_metadata = _ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', str(exc) ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	@fudge.patch('boto3.session.Session')
	def test_application_get(self, fake_session_factory):
		session = fake_session_factory.is_callable().returns_fake(name='Session')
		client_factory = session.provides('client').with_args('ses')
		(client_factory.returns_fake()
		 .expects( 'send_raw_email' ).returns( 'return' )
		 .expects('get_send_quota').returns( SEND_QUOTA ))
		# Initial condition
		res = self.testapp.get( '/dataserver2/@@bulk_email_admin/failed_username_recovery_email' )
		assert_that( res.body, contains_string( 'Start' ) )


		# Our notables run in a greenlet. Since we are not monkey
		# patched here, we temporarily override our transaction manager to
		# be gevent aware.
		import transaction
		from gevent._patcher import import_patched
		manager = import_patched('transaction._manager').module.ThreadTransactionManager()
		old_manager = transaction.manager
		transaction.manager = manager
		try:
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
		finally:
			transaction.manager = old_manager

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_application_get_template_dne(self):
		# Initial condition
		self.testapp.get( '/dataserver2/@@bulk_email_admin/no_such_template', status=404 )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_application_get_no_path(self):
		self.testapp.get( '/dataserver2/@@bulk_email_admin/', status=404 )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	@fudge.patch('boto3.session.Session')
	def test_application_policy_change(self, fake_session_factory):
		session = fake_session_factory.is_callable().returns_fake(name='Session')
		client_factory = session.provides('client').with_args('ses')
		(client_factory.returns_fake()
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


@contextlib.contextmanager
def modified_bulk_email_sender_for_site(ds, site_name, new_email):
	with mock_dataserver.mock_db_trans(ds, site_name=site_name):
		policy = component.queryUtility(ISitePolicyUserEventListener)
		original_sender = getattr(policy, 'DEFAULT_BULK_EMAIL_SENDER', '')
		policy.DEFAULT_BULK_EMAIL_SENDER = new_email
	try:
		yield
	finally:
		with mock_dataserver.mock_db_trans(ds, site_name=site_name):
			policy = component.queryUtility(ISitePolicyUserEventListener)
			policy.DEFAULT_BULK_EMAIL_SENDER = original_sender


