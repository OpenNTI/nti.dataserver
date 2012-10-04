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
from hamcrest import greater_than_or_equal_to
from hamcrest import is_not as does_not
from hamcrest import contains

from nti.tests import verifiably_provides
import anyjson as json
from zope import interface
from zope import component
from zope.component import eventtesting
from webtest import TestApp


from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces
from nti.appserver import site_policies
from nti.appserver import interfaces as app_interfaces
from nti.dataserver.tests import mock_dataserver

from .test_application import ApplicationTestBase
from . import ITestMailDelivery


class TestApplicationCoppaAdmin(ApplicationTestBase):

	def test_approve_coppa(self):
		"Basic tests of the moderation admin page"
		component.provideHandler( eventtesting.events.append, (None,) )
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			coppa_user = self._create_user( username='ossmkitty' )
			interface.alsoProvides( coppa_user, site_policies.IMathcountsCoppaUserWithoutAgreement )
			user_interfaces.IFriendlyNamed( coppa_user ).realname = u'Jason'

		testapp = TestApp( self.app )

		path = '/dataserver2/@@coppa_admin'
		environ = self._make_extra_environ()
		# Have to be in this policy
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'
		res = testapp.get( path, extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, contains_string( 'ossmkitty' ) )
		assert_that( res.body, contains_string( 'Jason' ) )

		# OK, now let's approve it, then we should be back to an empty page.
		# First, if we submit without an email, we don't get approval

		form = res.form
		form.set( 'table-coppa-admin-selected-0-selectedItems', True, index=0 )
		res = form.submit( 'subFormTable.buttons.approve', extra_environ=environ )
		assert_that( res.status_int, is_( 302 ) )

		res = testapp.get( path, extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, contains_string( 'ossmkitty' ) )
		assert_that( res.body, contains_string( 'Jason' ) )

		# Now, if we submit with an email, we do get approval
		form = res.form
		form.set( 'table-coppa-admin-selected-0-selectedItems', True, index=0 )
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
			assert_that( user, verifiably_provides( site_policies.IMathcountsCoppaUserWithAgreement ) )
			assert_that( user, verifiably_provides( user_interfaces.IRequireProfileUpdate ) )

			assert_that( user_interfaces.IFriendlyNamed( user ), has_property( 'realname', 'Jason' ) )
			assert_that( user_interfaces.IUserProfile( user ), has_property( 'contact_email', 'jason.madden@nextthought.com' ) )

			upgrade_event = eventtesting.getEvents( app_interfaces.IUserUpgradedEvent )[0]
			assert_that( upgrade_event, has_property( 'user', user ) )
			assert_that( upgrade_event, has_property( 'upgraded_interface', site_policies.IMathcountsCoppaUserWithAgreement ) )

		# We generated just the ack email
		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer, has_property( 'queue', has_length( 1 ) ) )
		assert_that( mailer, has_property( 'queue', contains( has_property( 'subject', 'NextThought Account Confirmation' ) ) ) )

		testapp.delete( '/dataserver2/users/ossmkitty/@@account.profile.needs.updated',
						extra_environ=self._make_extra_environ(username='ossmkitty'),
						status=204 )

		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( 'ossmkitty' )
			assert_that( user, does_not( verifiably_provides( user_interfaces.IRequireProfileUpdate ) ) )


	def test_post_contact_email_addr_sends_email(self):
		component.provideHandler( eventtesting.events.append, (None,) )
		with mock_dataserver.mock_db_trans( self.ds ):
			coppa_user = self._create_user( username='ossmkitty' )
			interface.alsoProvides( coppa_user, site_policies.IMathcountsCoppaUserWithoutAgreement )
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
			assert_that( user, verifiably_provides( site_policies.IMathcountsCoppaUserWithoutAgreement ) )
			assert_that( user_interfaces.IUserProfile( user ), has_property( 'contact_email', none() ) )

		# reset
		del mailer.queue[:]

		# Also can put to the field
		path = b'/dataserver2/users/ossmkitty/++fields++contact_email'
		data = 'jason.madden@nextthought.com'

		res = testapp.put( path, json.dumps( data ), extra_environ=self._make_extra_environ(username='ossmkitty') )
		assert_that( res.status_int, is_( 200 ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer, has_property( 'queue', has_length( 1 ) ) )
		assert_that( mailer, has_property( 'queue', contains( has_property( 'subject', "Please Confirm Your Child's NextThought Account" ) ) ) )


		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( 'ossmkitty' )
			assert_that( user, verifiably_provides( site_policies.IMathcountsCoppaUserWithoutAgreement ) )
			assert_that( user_interfaces.IUserProfile( user ), has_property( 'contact_email', none() ) )
