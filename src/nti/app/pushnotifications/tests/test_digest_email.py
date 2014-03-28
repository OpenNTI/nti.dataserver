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

import fudge


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
