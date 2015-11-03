#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import anyjson as json

from hamcrest import (assert_that, is_, none, has_entry, has_length, has_item, contains_string,  has_entries)
from hamcrest.library import has_property
from hamcrest import is_not as does_not
from hamcrest import contains

from zope import interface
from zope import component
from zope.component import eventtesting

from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces

from nti.appserver.policies import user_policies
from nti.appserver import interfaces as app_interfaces

from nti.dataserver.tests import mock_dataserver

from nti.appserver.tests import ITestMailDelivery

from nti.testing.matchers import validly_provides as verifiably_provides


from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.webtest import TestApp

from nti.app.sites.mathcounts.policy import MathcountsSitePolicyEventListener

class TestApplicationCoppaAdmin(ApplicationLayerTest):

	IF_ROOT = MathcountsSitePolicyEventListener.IF_ROOT
	IF_WOUT_AGREEMENT = MathcountsSitePolicyEventListener.IF_WOUT_AGREEMENT
	IF_WITH_AGREEMENT = MathcountsSitePolicyEventListener.IF_WITH_AGREEMENT

	@WithSharedApplicationMockDS
	def test_approve_coppa(self):
		#"Basic tests of the coppa admin page"
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			coppa_user = self._create_user( username='ossmkitty' )
			interface.alsoProvides( coppa_user, self.IF_WOUT_AGREEMENT )
			user_interfaces.IFriendlyNamed( coppa_user ).realname = u'Jason'

			# And a whole bunch of others for batching/paging reasons
			for i in range(300):
				u = self._create_user( username='TESTUSER' + str(i) )
				interface.alsoProvides( u, self.IF_WOUT_AGREEMENT )
				user_interfaces.IFriendlyNamed( u ).realname = u'TESTUSER' + str(i)

		testapp = TestApp( self.app )
		kittyapp = TestApp( self.app, extra_environ=self._make_extra_environ('ossmkitty') )

		path = '/dataserver2/@@coppa_admin'
		environ = self._make_extra_environ()
		# Have to be in this policy
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		# Begin by filtering out the user
		res = testapp.get( path + b'?usersearch=z', extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, does_not( contains_string( 'ossmkitty' ) ) )
		assert_that( res.body, does_not( contains_string( 'Jason' ) ) )

		# Ok, now for real.
		# We include some table batching/searching params to make sure that it works
		# even then. These are case-insensitive
		path = path + '?usersearch=OSSM'

		res = testapp.get( path , extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, contains_string( 'ossmkitty' ) )
		assert_that( res.body, contains_string( 'Jason' ) )

		assert_that( res.body, does_not( contains_string('TESTUSER') ))

		# OK, now let's approve it, then we should be back to an empty page.

		# First, if we submit without an email, we don't get approval,
		# we get an error message.
		form = res.forms['subFormTable']
		field_name = None
		for key in form.fields:
			if key.startswith( 'table-coppa-admin-selected' ):
				field_name = key
				break

		form.set( field_name, True, index=0 )

		res = form.submit( 'subFormTable.buttons.approve', extra_environ=environ )
		assert_that( res.status_int, is_( 302 ) )

		res = testapp.get( path, extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, contains_string( 'ossmkitty' ) )
		assert_that( res.body, contains_string( 'Jason' ) )
		assert_that( res.body, contains_string( 'No contact email provided for ossmkitty' ) )

		# Now, if we submit with an email, we do get approval
		form = res.forms['subFormTable']
		form.set( field_name, True, index=0 )
		for k in form.fields:
			if 'contactemail' in k:
				form.set( k, 'jason.madden@nextthought.com' )
		res = form.submit( 'subFormTable.buttons.approve', extra_environ=environ )
		assert_that( res.status_int, is_( 302 ) )

		res = testapp.get( path, extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.body, does_not( contains_string( 'ossmkitty' ) ) )
		assert_that( res.body, does_not( contains_string( 'Jason' ) ) )

		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( 'ossmkitty' )
			assert_that( user, verifiably_provides( self.IF_WITH_AGREEMENT ) )
			assert_that( user, verifiably_provides( user_interfaces.IRequireProfileUpdate ) )

			assert_that( user_interfaces.IFriendlyNamed( user ), has_property( 'realname', 'Jason' ) )
			assert_that( user_interfaces.IUserProfile( user ), has_property( 'contact_email', 'jason.madden@nextthought.com' ) )
			# assert_that( user, has_property( 'transitionTime', greater_than_or_equal_to(now)) )

			upgrade_event = eventtesting.getEvents( app_interfaces.IUserUpgradedEvent )[0]
			from ZODB.POSException import ConnectionStateError
			try:
				assert_that( upgrade_event, has_property( 'user', user ) )
			except ConnectionStateError:
				pass
			assert_that( upgrade_event, has_property( 'upgraded_interface', self.IF_WITH_AGREEMENT ) )

		# We generated just the ack email
		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer, has_property( 'queue', has_length( 1 ) ) )
		assert_that( mailer, has_property( 'queue', contains( has_property( 'subject', 'NextThought Account Confirmation' ) ) ) )

		# The schema should specify that an email address is required
		res = testapp.get( '/dataserver2/users/ossmkitty/@@account.profile',
						   extra_environ=self._make_extra_environ(username='ossmkitty'), )
		assert_that( res.json_body, has_entry( 'ProfileSchema', has_entry( 'email', has_entry( 'required', True ) ) ) )
		res = kittyapp.put( '/dataserver2/users/ossmkitty/++fields++email',
						   json.dumps( None ),
						   status=422 )
		assert_that( res.json_body, has_entry( 'field', 'email' ) )

		res = kittyapp.put( '/dataserver2/users/ossmkitty/++fields++email',
						   json.dumps( 'not_valid' ),
						   status=422 )
		assert_that( res.json_body, has_entry( 'field', 'email' ) )

		# We can't actually do anything until we get this email updated

		res = kittyapp.put( '/dataserver2/users/ossmkitty/++fields++NotificationCount',
						   json.dumps( 1 ),
						   status=422 )
		assert_that( res.json_body, has_entry( 'field', 'email' ) )

		# But what the hell, we can go ahead and clear the flag manually
		update_href = self.require_link_href_with_rel( self.resolve_user( kittyapp, 'ossmkitty' ), 'account.profile.needs.updated' )
		__traceback_info__ = update_href
		kittyapp.delete( update_href, status=204 )

		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( 'ossmkitty' )
			assert_that( user, does_not( verifiably_provides( user_interfaces.IRequireProfileUpdate ) ) )

	@WithSharedApplicationMockDS
	def test_post_contact_email_addr_sends_email(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			coppa_user = self._create_user( username='ossmkitty' )
			interface.alsoProvides( coppa_user, self.IF_WOUT_AGREEMENT )
			user_interfaces.IFriendlyNamed( coppa_user ).realname = u'Jason'

		testapp = TestApp( self.app )

		# The full user path
		path = b'/dataserver2/users/ossmkitty'
		data = {'contact_email': 'jason.madden@nextthought.com'}

		res = testapp.put( path, json.dumps( data ), extra_environ=self._make_extra_environ(username='ossmkitty') )
		assert_that( res.status_int, is_( 200 ) )



		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer, has_property( 'queue', has_length( 1 ) ) )
		assert_that( mailer, has_property( 'queue', contains( has_property( 'subject', "Please Confirm Your Child's NextThought Account" ) ) ) )

		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( 'ossmkitty' )
			assert_that( user, verifiably_provides( self.IF_WOUT_AGREEMENT ) )
			assert_that( user_interfaces.IUserProfile( user ), has_property( 'contact_email', none() ) )

		# reset
		del mailer.queue[:]

		# Also can put to the field, except it's too soon now
		path = b'/dataserver2/users/ossmkitty/++fields++contact_email'
		data = 'jason.madden@nextthought.com'

		res = testapp.put( path, json.dumps( data ), extra_environ=self._make_extra_environ(username='ossmkitty'), status=422 )
		assert_that( res.json_body, has_entry( 'code', 'AttemptingToResendConsentEmailTooSoon' ) )

		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( 'ossmkitty' )
			user_policies._clear_consent_email_rate_limit( user )

		# Now it works
		res = testapp.put( path, json.dumps( data ), extra_environ=self._make_extra_environ(username='ossmkitty'), status=200 )
		# We should be getting back a link to exactly that (see user_policies.py)
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entries( 'rel', 'contact-email-sends-consent-request',
																			   'href', path ) ) ) )



		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer, has_property( 'queue', has_length( 1 ) ) )
		assert_that( mailer, has_property( 'queue', contains( has_property( 'subject', "Please Confirm Your Child's NextThought Account" ) ) ) )

		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( 'ossmkitty' )
			assert_that( user, verifiably_provides( self.IF_WOUT_AGREEMENT ) )
			assert_that( user_interfaces.IUserProfile( user ), has_property( 'contact_email', none() ) )

	@WithSharedApplicationMockDS
	def test_profile_admin_get_view(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			coppa_user = self._create_user( username='ossmkitty' )
			interface.alsoProvides( coppa_user, self.IF_WOUT_AGREEMENT )
			user_interfaces.IFriendlyNamed( coppa_user ).realname = u'Jason'

		testapp = TestApp( self.app )

		path = '/dataserver2/users/ossmkitty/@@account_profile_view'
		environ = self._make_extra_environ()
		res = testapp.get( path, extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )
