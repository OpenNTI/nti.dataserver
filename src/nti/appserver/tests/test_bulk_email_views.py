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


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not as does_not
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import has_property

from nose.tools import assert_raises

import nti.tests

from nti.appserver import bulk_email_views

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS
import fudge
from fudge.inspector import arg

class TestBulkEmailProcess(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_preflight(self):
		process = bulk_email_views._Process('template_name')

		# all clear
		process.preflight_process()

		process.redis.set( process.names.lock_name, 'val' )
		assert process.redis.exists( process.names.lock_name )
		with assert_raises(bulk_email_views._PreflightError):
			process.preflight_process()

		# reset
		process.reset_process()
		process.preflight_process()

	@WithSharedApplicationMockDS
	def test_add_recipients(self):
		process = bulk_email_views._Process('template_name')

		# No email
		with assert_raises(ValueError):
			process.add_recipients( {} )

		process.preflight_process()

		process.add_recipients( {'email': 'foo@bar'}, {'email': 'biz@baz'} )
		assert_that( process.redis.scard(process.names.source_name), is_( 2 ) )

	@WithSharedApplicationMockDS
	@fudge.test
	def test_process_one_recipient(self):
		email = 'foo@bar'
		process = bulk_email_views._Process('failed_username_recovery_email')
		process.subject = 'Subject'
		fake_sesconn = fudge.Fake()
		(fake_sesconn.expects( 'send_raw_email' )
		 	.with_args( arg.any(), 'no-reply@alerts.nextthought.com', email )
			.returns( {'key': 'val'} ) )
		process.sesconn = fake_sesconn

		process.add_recipients( {'email': email} )

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )

		process.process_one_recipient()

		assert_that( process.redis.scard(process.names.source_name), is_( 0 ) )
		assert_that( process.redis.scard(process.names.dest_name), is_( 1 ) )

	@WithSharedApplicationMockDS
	@fudge.test
	def test_process_loop(self):
		email = 'foo@bar'
		process = bulk_email_views._Process('failed_username_recovery_email')
		process.subject = 'Subject'
		fake_sesconn = fudge.Fake()
		(fake_sesconn.expects( 'send_raw_email' )
		 	.with_args( arg.any(), 'no-reply@alerts.nextthought.com', email )
			.returns( {'key': 'val'} ) )
		process.sesconn = fake_sesconn

		process.add_recipients( {'email': email} )

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )

		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 0 ) )
		assert_that( process.redis.scard(process.names.dest_name), is_( 1 ) )

		fresh_metadata = bulk_email_views._ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', 'Completed' ) )


	@WithSharedApplicationMockDS
	@fudge.test
	def test_process_loop_quota_exceeded(self):
		email = 'foo@bar'
		process = bulk_email_views._Process('failed_username_recovery_email')
		process.subject = 'Subject'
		fake_sesconn = fudge.Fake()
		exc = bulk_email_views.SESDailyQuotaExceededError( "404", "Reason" )
		fake_sesconn.expects( 'send_raw_email' ).raises( exc )
		process.sesconn = fake_sesconn

		process.add_recipients( {'email': email} )

		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )

		fresh_metadata = bulk_email_views._ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', str(exc) ) )

	@WithSharedApplicationMockDS
	@fudge.test
	def test_process_loop_seserror(self):
		email = 'foo@bar'
		process = bulk_email_views._Process('failed_username_recovery_email')
		process.subject = 'Subject'
		fake_sesconn = fudge.Fake()
		exc = bulk_email_views.SESError( "404", "Reason" )
		fake_sesconn.expects( 'send_raw_email' ).raises( exc )
		process.sesconn = fake_sesconn

		process.add_recipients( {'email': email} )

		process.process_loop()

		assert_that( process.redis.scard(process.names.source_name), is_( 1 ) )
		assert_that( process.__dict__, does_not( has_key( 'sesconn' ) ) )

		fresh_metadata = bulk_email_views._ProcessMetaData( process.redis, process.names.metadata_name )
		assert_that( fresh_metadata, has_property( 'status', str(exc) ) )
