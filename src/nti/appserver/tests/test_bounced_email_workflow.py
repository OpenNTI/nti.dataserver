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

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_property

from zope.lifecycleevent import modified
import anyjson as json
import os

from boto.sqs.message import RawMessage

from nti.app.testing.layers import SharedConfiguringTestLayer
from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests import mock_dataserver
from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.users.user_profile import make_password_recovery_email_hash


from .test_application import TestApp

from nti.appserver import bounced_email_workflow
from nti.appserver.link_providers import flag_link_provider as user_link_provider

def _read_msgs(make_perm=False):
	msg_str = open( os.path.join( os.path.dirname( __file__ ), 'bounced_email_feedback_transients.json' ), 'r' ).read()
	if make_perm:
		msg_str = msg_str.replace( 'Transient', 'Permanent' )
	msg_objs = json.loads( msg_str )

	messages = [RawMessage( body=json.dumps(x) ) for x in msg_objs]
	return messages

from hamcrest.core.base_matcher import BaseMatcher

class _HasLinkMatcher(BaseMatcher):
	def __init__( self, value ):
		super(_HasLinkMatcher,self).__init__()
		self.value = value

	def _matches( self, item ):
		return user_link_provider.has_link( item, self.value )

	def describe_to( self, description ):
		description.append_text( 'user having link ' ).append( str(self.value) )

	def __repr__( self ):
		return 'user having link ' + str(self.value)

has_link = _HasLinkMatcher

from nti.mailer.interfaces import IVERP
import rfc822
from zope import component

class _TrivialVerp(object):

	def principal_ids_from_verp(self, fromaddr, request=None):
		if '+' not in fromaddr:
			return ()

		_, addr = rfc822.parseaddr(fromaddr)
		return (addr.split('+', 1)[1].split('@')[0],)

class TestBouncedEmailworkflow(unittest.TestCase):
	layer = SharedConfiguringTestLayer

	def setUp(self):
		self._old_verp = component.getUtility(IVERP)
		component.provideUtility(_TrivialVerp(), IVERP)

	def tearDown(self):
		component.provideUtility(self._old_verp, IVERP)

	def test_process_transient_messages(self):
		messages = _read_msgs()
		# no dataserver needed, because they're all transient
		proc, _ = bounced_email_workflow.process_ses_feedback( messages, mark_transient=False )
		assert_that( proc, is_( messages ) )


	@WithMockDSTrans
	def test_process_permanent_bounces(self):
		messages = _read_msgs( make_perm=True )
		proc, _ = bounced_email_workflow.process_ses_feedback( messages )
		# But no users have these email addresses, so nothing actually happened
		assert_that( proc, is_( messages ) )

	@WithMockDSTrans
	def test_process_permanent_bounces_find_users(self):

		u1 = users.User.create_user( username='user1' )
		user_interfaces.IUserProfile( u1 ).email = 'n@y.com'
		modified( u1 )
		u2 = users.User.create_user( username='user2' )
		user_interfaces.IUserProfile( u2 ).password_recovery_email_hash = make_password_recovery_email_hash( 'n@y.com' )
		modified( u2 )
		u3 = users.User.create_user( username='user3' )
		user_interfaces.IUserProfile( u3 ).contact_email = 'n@y.com'
		modified( u3 )
		u4 = users.User.create_user( username='user4' )
		user_interfaces.IContactEmailRecovery( u4 ).contact_email_recovery_hash = make_password_recovery_email_hash( 'n@y.com' )
		modified( u4 )

		messages = _read_msgs( make_perm=True )
		proc, matched = bounced_email_workflow.process_ses_feedback( messages )
		assert_that( proc, is_( messages ) )
		assert_that( matched, has_length(4) )

		assert_that( u1, has_link( bounced_email_workflow.REL_INVALID_EMAIL ) )
		assert_that( u2, has_link( bounced_email_workflow.REL_INVALID_EMAIL ) )
		assert_that( u3, has_link( bounced_email_workflow.REL_INVALID_CONTACT_EMAIL ) )
		assert_that( u4, has_link( bounced_email_workflow.REL_INVALID_CONTACT_EMAIL ) )

class TestApplicationBouncedEmailWorkflow(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_delete_states(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			user_username = user.username
			user_link_provider.add_link( user, bounced_email_workflow.REL_INVALID_CONTACT_EMAIL )
			user_link_provider.add_link( user, bounced_email_workflow.REL_INVALID_EMAIL )


		testapp = TestApp( self.app, extra_environ=self._make_extra_environ() )

		for k in (bounced_email_workflow.REL_INVALID_EMAIL,bounced_email_workflow.REL_INVALID_CONTACT_EMAIL):
			href = self.require_link_href_with_rel( self.resolve_user( testapp, user_username ), k )

			res = testapp.delete( href , extra_environ=self._make_extra_environ() )
			assert_that( res, has_property( 'status_int', 204 ) )

			res = testapp.delete( href, extra_environ=self._make_extra_environ(), status=404 )
			assert_that( res, has_property( 'status_int', 404 ) )
