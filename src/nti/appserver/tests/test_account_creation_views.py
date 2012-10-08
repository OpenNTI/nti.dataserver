#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"


#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

logger = __import__('logging').getLogger(__name__)


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import contains_string
from hamcrest import is_not as does_not
from hamcrest import has_property
from hamcrest import greater_than
from hamcrest import has_item
from hamcrest import greater_than_or_equal_to

from nti.tests import verifiably_provides
from nose.tools import assert_raises
import itertools

from nti.appserver import interfaces as app_interfaces
from nti.appserver.account_creation_views import account_create_view, account_preflight_view
from nti.appserver import site_policies
from nti.appserver import z3c_zpt
from nti.appserver.tests import NewRequestSharedConfiguringTestBase as SharedConfiguringTestBase, ITestMailDelivery

import pyramid.httpexceptions as hexc
import pyramid.interfaces

from nti.dataserver.interfaces import IShardLayout, INewUserPlacer
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
import nti.dataserver.tests.mock_dataserver
from nti.dataserver import shards
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.externalization.externalization import to_json_representation
from nti.externalization.externalization import to_external_object
from nti.dataserver.users import interfaces as user_interfaces

from zope.component import eventtesting
from zope import component
from zope.lifecycleevent import IObjectCreatedEvent, IObjectAddedEvent
from zope.annotation.interfaces import IAnnotations

import datetime



class _AbstractValidationViewBase(SharedConfiguringTestBase):
	""" Base for the things where validation should fail """

	the_view = None

	def setUp(self):
		super(_AbstractValidationViewBase,self).setUp()

	@WithMockDSTrans
	def test_create_invalid_realname(self):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': '123 456_',
													 'email': 'foo@bar.com',} )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			self.the_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'realname' ) )
		assert_that( exc.exception.json_body, has_entry( 'code', 'RealnameInvalid' ) )
		assert_that( exc.exception.json_body, has_entry( 'value', '123 456_' ) )
		assert_that( exc.exception.json_body, has_entry( 'message', contains_string( 'The first or last name you have entered is not valid.' ) ) )

	@WithMockDSTrans
	def test_create_invalid_invitation_code(self):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com',
													 'invitation_codes': ['foobar'] } )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			self.the_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'invitation_codes' ) )
		assert_that( exc.exception.json_body, has_entry( 'code', 'InvitationCodeError' ) )
		assert_that( exc.exception.json_body, has_entry( 'value', 'foobar' ) )
		assert_that( exc.exception.json_body, has_entry( 'message', contains_string( 'The invitation code is not valid.' ) ) )

	@WithMockDSTrans
	def test_create_valid_invitation_code(self):
		users.Community.create_entity( username='MATHCOUNTS' )
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com',
													 'invitation_codes': ['MATHCOUNTS'] } )

		self.the_view( self.request )


	@WithMockDSTrans
	def test_create_invalid_password(self):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar.com',
													 'email': 'foo@bar.com',
													 'password': 'a' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			self.the_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'password' ) )
		assert_that( exc.exception.json_body, has_entry( 'message', contains_string( 'Your password is too short. Please choose one at least' ) ) )
		assert_that( exc.exception.json_body, has_entry( 'code', 'TooShortPassword' ) )


	@WithMockDSTrans
	def test_create_invalid_email( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass132word',
													 'email': 'not valid' } )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'email' ) )



	@WithMockDSTrans
	def test_create_invalid_username( self ):
		self.request.content_type = 'application/vnd.nextthought+json'

		bad_code = 'UsernameCannotBeBlank'
		bad_code = [bad_code] + ['UsernameContainsIllegalChar'] * 4
		bad_code.append( "TooShort" )
		for bad_code, bad_username in itertools.izip( bad_code, ('   ', 'foo bar', 'foo#bar', 'foo,bar', 'foo%bar', 'abcd' )):

			self.request.body = to_json_representation( {'Username': bad_username,
														 'password': 'pass132word',
														 'realname': 'Joe Human',
														 'email': 'user@domain.com' } )
			__traceback_info__ = self.request.body


			with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
				self.the_view( self.request )

			assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )
			assert_that( e.exception.json_body, has_entry( 'code', bad_code ) )

		# last one is too short.
		assert_that( e.exception.json_body, has_entry( 'message', contains_string('Username is too short. Please use at least' ) ) )


class _AbstractNotDevmodeViewBase(SharedConfiguringTestBase):
	# The tests that depend on not having devmode installed (stricter defailt validation) should be here
	# Since they run so much slower due to the mimetype registration
	features = ()

	the_view = None

	def setUp(self):
		super(_AbstractNotDevmodeViewBase,self).setUp()

	@WithMockDSTrans
	def test_create_censored_username( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'shpxsnpr'.encode('rot13'),
													 'password': 'pass132word',
													 'email': 'foo@bar.com' } )


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'FieldContainsCensoredSequence' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'censored' ) ) )


	@WithMockDSTrans
	def test_create_censored_alias( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'alias': 'shpxsnpr'.encode('rot13'),
													 'Username': 'jamadden',
													 'password': 'pass132word',
													 'email': 'foo@bar.com' } )


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'FieldContainsCensoredSequence' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'alias' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'censored' ) ) )

	@WithMockDSTrans
	def test_create_birthdate_must_be_in_past( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {
													 'Username': 'jamadden',
													 'realname': 'Jason Madden',
													 'password': 'pass132word',
													 'email': 'foo@bar.com',
													 'birthdate': datetime.date.today().isoformat() } )


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'BirthdateInFuture' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'birthdate' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'past' ) ) )

	@WithMockDSTrans
	def test_create_birthdate_two_digit_year( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		# This two-digit year is interpreted as in the future
		self.request.body = to_json_representation( {
													 'Username': 'jamadden',
													 'realname': 'Jason Madden',
													 'password': 'pass132word',
													 'email': 'foo@bar.com',
													 'birthdate': '63-01-01' } )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'BirthdateInFuture' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'birthdate' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'past' ) ) )

	@WithMockDSTrans
	def test_create_birthdate_must_be_four_years_ago( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		today = datetime.date.today()
		three_years_ago = today.replace( year=today.year - 3 )
		self.request.body = to_json_representation( {
													 'Username': 'jamadden',
													 'realname': 'Jason Madden',
													 'password': 'pass132word',
													 'email': 'foo@bar.com',
													 'birthdate': three_years_ago.isoformat() } )


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'BirthdateTooRecent' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'birthdate' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'four' ) ) )

	@WithMockDSTrans
	def test_create_blank_realname( self ):

		self.request.content_type = 'application/vnd.nextthought+json'

		self.request.body = to_json_representation( {'Username': 'this_username_works',
													 'password': 'pass132word',
													 'realname': '',
													 'email': 'user@domain.com' } )
		__traceback_info__ = self.request.body


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'field', 'realname' ) )
		assert_that( e.exception.json_body, has_entry( 'code', 'BlankHumanNameError' ) )
		assert_that( e.exception.json_body, has_entry( 'message', 'Please provide your first and last names.' ) )

	@WithMockDSTrans
	def test_create_invalid_realname( self ):

		self.request.content_type = 'application/vnd.nextthought+json'

		self.request.body = to_json_representation( {'Username': 'this_username_works',
													 'password': 'pass132word',
													 'realname': 'Joe',
													 'email': 'user@domain.com' } )
		__traceback_info__ = self.request.body


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'field', 'realname' ) )
		assert_that( e.exception.json_body, has_entry( 'code', 'MissingLastName' ) )
		assert_that( e.exception.json_body, has_entry( 'message', 'Please provide your first and last names.' ) )


class TestPreflightView(_AbstractValidationViewBase):


	def setUp( self ):
		super(TestPreflightView,self).setUp()
		self.the_view = account_preflight_view

	@WithMockDSTrans
	def test_create_mathcounts_policy_birthdate_only_old_user( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'

		self.request.body = to_json_representation( {
													 'birthdate': '1982-01-31',
													  }  )

		val = self.the_view( self.request )

		assert_that( val, has_entry( 'AvatarURLChoices', has_length( 0 ) ) )
		assert_that( val, has_entry( 'ProfileSchema', has_key( 'opt_in_email_communication' ) ) )
		assert_that( val, has_entry( 'ProfileSchema', has_entry( 'Username', has_entry( 'min_length', 5 ) ) ) )
		assert_that( val, has_entry( 'ProfileSchema',
									 has_entry( 'password',
												has_entry( 'required', True ) ) ) )

		assert_that( val, has_entry( 'ProfileSchema',
									 has_entry( 'participates_in_mathcounts',
												has_entry( 'required', False ) ) ) )
		assert_that( val, has_entry( 'ProfileSchema',
									 has_entry( 'participates_in_mathcounts',
												has_entry( 'type', 'bool' ) ) ) )

		assert_that( val, has_entry( 'ProfileSchema',
									 has_entry( 'role',
												has_key( 'choices' ) ) ) )
		assert_that( val, has_entry( 'ProfileSchema',
									 has_entry( 'affiliation',
												has_entry( 'type', 'nti.appserver.site_policies.school' ) ) ) )


	@WithMockDSTrans
	def test_create_invalid_realname_mathcounts( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'
		self.request.content_type = 'application/vnd.nextthought+json'

		bad_code = 'UsernameCannotBeBlank'
		birthdate = datetime.date.today().replace( year=datetime.date.today().year - 10 ).isoformat()
		self.request.body = to_json_representation( { 'birthdate': birthdate,
													 'realname': 'N K' } )
		__traceback_info__ = self.request.body


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )
		assert_that( e.exception.json_body, has_entry( 'code', bad_code ) )

	@WithMockDSTrans
	def test_create_special_characters_username_mathcounts( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'
		self.request.content_type = 'application/vnd.nextthought+json'

		bad_code = 'UsernameContainsIllegalChar'
		birthdate = datetime.date.today().replace( year=datetime.date.today().year - 10 ).isoformat()
		self.request.body = to_json_representation( { 'Username': 'test#%^&',
													  'birthdate': birthdate,
													  'realname': 'N K' } )
		__traceback_info__ = self.request.body


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )
		assert_that( e.exception.json_body, has_entry( 'code', bad_code ) )
		assert_that( e.exception.json_body, has_entry( 'message',
													  'Username contains an illegal character. Only letters, digits, and +-_. are allowed.' ) )


	@WithMockDSTrans
	def test_create_mathcounts_policy_birthdate_only_under_13_user( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'

		birthdate = datetime.date.today().replace( year=datetime.date.today().year - 10 ).isoformat()

		self.request.body = to_json_representation( {
													 'birthdate': birthdate,
													  }  )

		val = self.the_view( self.request )

		assert_that( val, has_entry( 'AvatarURLChoices', has_length( 0 ) ) )
		assert_that( val, has_entry( 'ProfileSchema', does_not( has_key( 'opt_in_email_communication' ) ) ) )
		assert_that( val, has_entry( 'ProfileSchema',
									 has_entry( 'contact_email',
												has_entry( 'required', True ) ) ) )

		assert_that( val, has_entry( 'ProfileSchema',
									 has_entry( 'participates_in_mathcounts',
												has_entry( 'required', False ) ) ) )
		assert_that( val, has_entry( 'ProfileSchema',
									 has_entry( 'participates_in_mathcounts',
												has_entry( 'type', 'bool' ) ) ) )


	@WithMockDSTrans
	def test_create_mathcounts_policy_avatar_choices( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'
		birthdate = datetime.date.today().replace( year=datetime.date.today().year - 10 ).isoformat()
		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'realname': 'Joe Bananna',
													 'birthdate': birthdate,
													 'alias': 'jason_nextthought_com' }  )

		val = self.the_view( self.request )
		assert_that( val, has_entry( 'AvatarURLChoices', has_length( greater_than_or_equal_to( 8 ) ) ) )
		assert_that( val, has_entry( 'ProfileSchema', does_not( has_key( 'opt_in_email_communication' ) ) ) )
		assert_that( val, has_entry( 'ProfileSchema', has_key( 'contact_email' ) ) )


	@WithMockDSTrans
	def test_create_rwanda_policy_avatar_choices( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://rwanda.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'birthdate': '1982-01-31',
													 'alias': 'Jason',
													 'affiliation': 'NTI',
													 'email': 'jason@test.nextthought.com' } )
		new_user = self.the_view( self.request )
		assert_that( new_user, has_entry( 'AvatarURLChoices', has_length( 0 ) ) )

	@WithMockDSTrans
	def test_preflight_username_only_with_email( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://rwanda.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'birthdate': '1982-01-31'} )
		new_user = self.the_view( self.request )
		assert_that( new_user, has_entry( 'AvatarURLChoices', has_length( 0 ) ) )

		self.request.body = to_json_representation( {'Username': 'jason@example',
													 'birthdate': '1982-01-31'} )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )
		assert_that( e.exception.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )
		assert_that( e.exception.json_body, has_entry( 'message', 'The email address you have entered is not valid.' ) )


class TestCreateViewNotDevmode(_AbstractNotDevmodeViewBase):

	def setUp( self ):
		super(TestCreateViewNotDevmode,self).setUp()
		self.the_view = account_create_view

	@WithMockDSTrans
	def test_create_works( self ):
		# username result
		# events
		# headers
		component.provideHandler( eventtesting.events.append, (None,) )
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com' } )


		new_user = account_create_view( self.request )
		assert_that( new_user, has_property( 'username', 'jason@test.nextthought.com' ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'alias', 'Jason Madden' ) )
		assert_that( self.request.response, has_property( 'location', contains_string( '/dataserver2/users/jason%40test.nextthought.com' ) ) )
		assert_that( self.request.response, has_property( 'status_int', 201 ) )
		#assert_that( self.request.response.headers, has_property( "what", "th" ) )

		assert_that( eventtesting.getEvents(  ), has_length( greater_than( 2 ) ) )
		assert_that( eventtesting.getEvents( app_interfaces.IUserLogonEvent ), has_length( 1 ) )
		assert_that( eventtesting.getEvents( IObjectCreatedEvent, lambda x: x.object is new_user ), has_length( 1 ) )
		assert_that( eventtesting.getEvents( IObjectAddedEvent, lambda x: x.object is new_user ), has_length( 1 ) )

	@WithMockDSTrans
	def test_create_duplicate( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass132word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com' } )

		new_user = account_create_view( self.request )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'alias', 'Jason Madden' ) )

		with assert_raises( hexc.HTTPConflict ) as e:
			account_create_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'DuplicateUsernameError' ) )

	@WithMockDSTrans
	def _do_test_create_site_policy( self, host, com_name ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://' + host

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'birthdate': '1982-01-31',
													 'alias': 'Jason',
													 'affiliation': 'NTI',
													 # Email is copied automatically
													 #'email': 'jason@test.nextthought.com'
													 } )
		new_user = account_create_view( self.request )
		assert_that( new_user, has_property( 'communities', has_item( com_name ) ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'realname', 'Jason Madden' ) )
		assert_that( user_interfaces.ICompleteUserProfile( new_user ),
					 has_property( 'birthdate', datetime.date( 1982, 1, 31 ) ) )

		assert_that( to_external_object( new_user ), has_entries( 'email', 'jason@test.nextthought.com',
																  'birthdate', '1982-01-31',
																  'affiliation', 'NTI' ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_item( has_property( 'subject', 'Welcome to NextThought' ) ) )

	def test_create_rwanda_policy( self ):
		self._do_test_create_site_policy( 'rwanda.nextthought.com', 'CarnegieMellonUniversity' )

	def test_create_law_policy( self ):
		self._do_test_create_site_policy( 'law.nextthought.com', 'law.nextthought.com' )

	def test_create_prmia_policy( self ):
		self._do_test_create_site_policy( 'prmia.nextthought.com', 'prmia.nextthought.com' )

class TestCreateView(_AbstractValidationViewBase):

	def setUp( self ):
		super(TestCreateView,self).setUp()
		self.the_view = account_create_view

	@WithMockDSTrans
	def test_create_missing_username( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'password': 'pass123word', 'email': 'foo@bar.com' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ):
			self.the_view( self.request )


	@WithMockDSTrans
	def test_create_missing_password(self):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar.com', 'email': 'foo@bar.com' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ):
			account_create_view( self.request )

	@WithMockDSTrans
	def test_create_null_password(self):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar.com',
													 'email': 'foo@bar.com',
													 'password': None } )
		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			self.the_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'password' ) )
		#assert_that( exc.exception.json_body, has_entry( 'message', contains_string( 'Password is too short' ) ) )
		#assert_that( exc.exception.json_body, has_entry( 'code', 'TooShortPassword' ) )

	@WithMockDSTrans
	def test_create_shard_matches_request_host( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		mock_dataserver.add_memory_shard( self.ds, 'example.com' )

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com' } )


		new_user = account_create_view( self.request )

		assert_that( new_user._p_jar.db(), has_property( 'database_name', 'example.com' ) )

		assert_that( new_user, has_property( '__parent__', IShardLayout( mock_dataserver.current_transaction ).users_folder ) )

	@WithMockDSTrans
	def test_create_shard_matches_request_origin( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://content.nextthought.com'
		mock_dataserver.add_memory_shard( self.ds, 'content.nextthought.com' )

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com' } )


		new_user = account_create_view( self.request )

		assert_that( new_user._p_jar.db(), has_property( 'database_name', 'content.nextthought.com' ) )

		assert_that( new_user, has_property( '__parent__', IShardLayout( mock_dataserver.current_transaction ).users_folder ) )

	@WithMockDSTrans
	def test_create_mathcounts_policy_email_required( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'

		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'realname': 'Joe Bananna',
													 'birthdate': '1982-01-31',
													 'alias': 'jason_nextthought_com' }  )
		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			 self.the_view( self.request )

		assert_that( exc.exception.json_body, has_entry( 'field', 'email' ) )

	@WithMockDSTrans
	def test_create_mathcounts_policy_contact_email_required_valid( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'

		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'realname': 'Joe Bananna',
													 'email': 'foo@bar.com',
													 'contact_email': 'other',
													 'alias': 'jason_nextthought_com' }  )
		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			 self.the_view( self.request )

		assert_that( exc.exception.json_body, has_entry( 'field', 'contact_email' ) )

		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'realname': 'Joe Bananna',
													 'email': 'foo@bar.com',
													 'contact_email': 'other@other.com',
													 'alias': 'jason_nextthought_com' }  )
		new_user = self.the_view( self.request )
		# We sent mail
		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		assert_that( mailer.queue[0], has_property( 'body', contains_string( 'Parent' ) ) )
		# and destroyed the evidence
		assert_that( user_interfaces.IUserProfile( new_user ),
					 has_property( 'contact_email', None ) )

	@WithMockDSTrans
	def test_create_mathcounts_policy( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'
		mailer = component.getUtility( ITestMailDelivery )

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'email': 'foo@bar.com' } )


		with assert_raises( hexc.HTTPUnprocessableEntity ):
			# Cannot include username
			account_create_view( self.request )

		# Our value for alias trumps anything they send
		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'realname': 'Joe Bananna',
													 'alias': 'Me',
													 #'email': 'foo@bar.com',
													 'contact_email': 'foo@bar.com' } )

		new_user = account_create_view( self.request )
		assert_that( user_interfaces.IFriendlyNamed( new_user ),
					 has_property( 'alias', new_user.username ) )
		# We sent no birthdate so we must assume it's a baby
		assert_that( new_user, verifiably_provides( nti_interfaces.ICoppaUserWithoutAgreement ) )
		assert_that( new_user, verifiably_provides( site_policies.IMathcountsCoppaUserWithoutAgreement ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'realname', 'Joe' ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ),
					 has_property( 'participates_in_mathcounts', False ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ),
					 has_property( 'email', None ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ),
					 has_property( 'password_recovery_email_hash', '823776525776c8f23a87176c59d25759da7a52c4' ) )

		# Which means we sent no mail, except to the parent
		assert_that( mailer.queue, has_length( 1 ) )
		from .. import user_policies
		assert_that( IAnnotations(new_user), has_entry( user_policies.CONTACT_EMAIL_RECOVERY_ANNOTATION, '823776525776c8f23a87176c59d25759da7a52c4' ) )


		assert_that( to_external_object( new_user ), has_entries( 'email', None,
																  'birthdate', None,
																  'affiliation', None,
																  'participates_in_mathcounts', False ) )


		# This guy is old enough to require an email and not need a contact_email
		self.request.body = to_json_representation( {'Username': 'jason2_nextthought_com',
													 'password': 'pass123word',
													 'realname': 'Joe Bananna',
													 'birthdate': '1982-01-31',
													 'affiliation': 'school',
													 'email': 'foo@bar.com' } )
		new_user = account_create_view( self.request )
		assert_that( new_user, verifiably_provides( nti_interfaces.ICoppaUserWithAgreement ) )
		assert_that( new_user, verifiably_provides( site_policies.IMathcountsCoppaUserWithAgreement ) )
		assert_that( new_user, has_property( 'communities', has_item( 'MATHCOUNTS' ) ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'realname', 'Joe Bananna' ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ),
					 has_property( 'birthdate', datetime.date( 1982, 1, 31 ) ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ),
					 has_property( 'affiliation', 'school' ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ),
					 has_property( 'role', 'Other' ) )

		# He's old enough we can echo this stuff back
		assert_that( to_external_object( new_user ), has_entries( 'email', 'foo@bar.com',
																  'birthdate', '1982-01-31',
																  'affiliation', 'school',
																  'role', 'Other' ) )
		# And we sent mail
		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_item( has_property( 'subject', 'Welcome to NextThought' ) ) )


	@WithMockDSTrans
	def _do_test_create_site_policy( self, host, com_name ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://' + host

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'birthdate': '1982-01-31',
													 'alias': 'Jason',
													 'affiliation': 'NTI',
													 # Email is copied automatically
													 #'email': 'jason@test.nextthought.com'
													 } )
		new_user = account_create_view( self.request )
		assert_that( new_user, has_property( 'communities', has_item( com_name ) ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'realname', 'Jason Madden' ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'alias', 'Jason Madden' ) )
		assert_that( user_interfaces.ICompleteUserProfile( new_user ),
					 has_property( 'birthdate', datetime.date( 1982, 1, 31 ) ) )

		assert_that( to_external_object( new_user ), has_entries( 'email', 'jason@test.nextthought.com',
																  'birthdate', '1982-01-31',
																  'affiliation', 'NTI' ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_item( has_property( 'subject', 'Welcome to NextThought' ) ) )

	def test_create_rwanda_policy( self ):
		self._do_test_create_site_policy( 'rwanda.nextthought.com', 'CarnegieMellonUniversity' )

	def test_create_law_policy( self ):
		self._do_test_create_site_policy( 'law.nextthought.com', 'law.nextthought.com' )

	def test_create_prmia_policy( self ):
		self._do_test_create_site_policy( 'prmia.nextthought.com', 'prmia.nextthought.com' )


	@WithMockDSTrans
	def test_create_component_matches_request_host( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		mock_dataserver.add_memory_shard( self.ds, 'FOOBAR' )
		class Placer(shards.AbstractShardPlacer):
			def placeNewUser( self, user, users_directory, _shards ):
				self.place_user_in_shard_named( user, users_directory, 'FOOBAR' )
		utility = Placer()
		component.provideUtility( utility, provides=INewUserPlacer, name='example.com' )
		try:
			self.request.content_type = 'application/vnd.nextthought+json'
			self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
														 'password': 'pass123word',
														 'realname': 'Jason Madden',
														 'email': 'foo@bar.com' } )


			new_user = account_create_view( self.request )

			assert_that( new_user._p_jar.db(), has_property( 'database_name', 'FOOBAR' ) )

			assert_that( new_user, has_property( '__parent__', IShardLayout( mock_dataserver.current_transaction ).users_folder ) )
		finally:
			component.getGlobalSiteManager().unregisterUtility( utility, provided=INewUserPlacer, name='example.com' )

from .test_application import ApplicationTestBase, WithSharedApplicationMockDS, SharedApplicationTestBase
from webtest import TestApp
from nti.dataserver.tests import mock_dataserver

class _AbstractApplicationCreateUserTest(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_create_user( self ):
		app = TestApp( self.app )

		data = to_json_representation( {'Username': 'jason@test.nextthought.com',
										'password': 'password',
										'realname': 'Jason Madden',
										'email': 'foo@bar.com'	} )

		path = b'/dataserver2/users/@@account.create'

		res = app.post( path, data )

		assert_that( res, has_property( 'status_int', 201 ) )
		assert_that( res, has_property( 'location', contains_string( '/dataserver2/users/jason' ) ) )

		assert_that( res.headers, has_key( 'Set-Cookie' ) )
		assert_that( res.json_body, has_entry( 'Username', 'jason@test.nextthought.com' ) )
		return res

class TestApplicationCreateUserNonDevmode(_AbstractApplicationCreateUserTest):
	features = ()
	APP_IN_DEVMODE = False

	@WithSharedApplicationMockDS
	def test_create_user( self ):
		super(TestApplicationCreateUserNonDevmode,self).test_create_user()
		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_item( has_property( 'subject', 'Welcome to NextThought' ) ) )


class TestApplicationCreateUser(_AbstractApplicationCreateUserTest):

	@WithSharedApplicationMockDS
	def test_create_user( self ):
		super(TestApplicationCreateUser,self).test_create_user()
		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 0 ) ) # no email in devmode because there is no site policy

	@WithSharedApplicationMockDS
	def test_create_user_mathcounts_policy( self ):

		app = TestApp( self.app )

		data = to_json_representation(  {'Username': 'jason2_nextthought_com',
										 'password': 'pass123word',
										 'realname': 'Joe Bananna',
										 'birthdate': '1982-01-31',
										 'affiliation': 'school',
										 'email': 'foo@bar.com' } )

		path = b'/dataserver2/users/@@account.create'

		res = app.post( path, data, extra_environ={b'HTTP_ORIGIN': b'http://mathcounts.nextthought.com'} )

		assert_that( res, has_property( 'status_int', 201 ) )
		assert_that( res, has_property( 'location', contains_string( '/dataserver2/users/jason' ) ) )

		assert_that( res.cookies_set, has_key( 'nti.auth_tkt' ) )
		assert_that( res.cookies_set, has_key( 'nti.landing_page' ) )
		assert_that( res.json_body, has_entry( 'Username', 'jason2_nextthought_com' ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_item( has_property( 'subject', 'Welcome to NextThought' ) ) )
		# Be sure we picked up the right template
		assert_that( mailer.queue, has_item( has_property( 'body', contains_string( 'MATHCOUNTS' ) ) ) )

	@WithSharedApplicationMockDS
	def test_create_coppa_user_mathcounts_policy( self ):

		app = TestApp( self.app )

		data = to_json_representation(  {'Username': 'jason2_nextthought_com',
										 'password': 'pass123word',
										 'realname': 'Joe Bananna',
										 'birthdate': '2008-01-31', # NOTE: This will break after the year 2021
										 'affiliation': 'school',
										 'email': 'foo@bar.com',
										 'contact_email': 'jason.madden@nextthought.com' } )

		path = b'/dataserver2/users/@@account.create'

		res = app.post( path, data, extra_environ={b'HTTP_ORIGIN': b'http://mathcounts.nextthought.com'} )

		assert_that( res, has_property( 'status_int', 201 ) )
		assert_that( res, has_property( 'location', contains_string( '/dataserver2/users/jason' ) ) )

		assert_that( res.cookies_set, has_key( 'nti.auth_tkt' ) )
		assert_that( res.cookies_set, has_key( 'nti.landing_page' ) )
		assert_that( res.json_body, has_entry( 'Username', 'jason2_nextthought_com' ) )
		assert_that( res.json_body, has_entry( 'alias', 'jason2_nextthought_com' ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer, has_property( 'queue', has_item( has_property( 'subject', "Please Confirm Your Child's NextThought Account" ) ) ) )

		del mailer.queue[:]

	@WithSharedApplicationMockDS
	def test_create_user_prmia_policy( self ):

		app = TestApp( self.app )

		data = to_json_representation(  {'Username': 'jason2_nextthought_com',
										 'password': 'pass123word',
										 'realname': 'Joe Bananna',
										 'birthdate': '1982-01-31',
										 'affiliation': 'school',
										 'email': 'foo@bar.com' } )

		path = b'/dataserver2/users/@@account.create'

		res = app.post( path, data, extra_environ={b'HTTP_ORIGIN': b'http://prmia.nextthought.com'} )

		assert_that( res, has_property( 'status_int', 201 ) )
		assert_that( res, has_property( 'location', contains_string( '/dataserver2/users/jason' ) ) )

		assert_that( res.cookies_set, has_key( 'nti.auth_tkt' ) )
		assert_that( res.cookies_set, has_key( 'nti.landing_page' ) )
		assert_that( res.json_body, has_entry( 'Username', 'jason2_nextthought_com' ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_item( has_property( 'subject', 'Welcome to NextThought' ) ) )
		# Be sure we picked up the right template
		assert_that( mailer.queue, has_item( has_property( 'body', does_not( contains_string( 'MATHCOUNTS' ) ) ) ) )

	@WithSharedApplicationMockDS
	def test_create_user_logged_in( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user( )

		app = TestApp( self.app )
		data = to_json_representation( {'Username': 'jason@test.nextthought.com',
										'password': 'password' } )

		path = b'/dataserver2/users/@@account.create'

		_ = app.post( path, data, extra_environ=self._make_extra_environ(), status=403 )

class TestApplicationPreflightUser(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_preflight_user( self ):
		app = TestApp( self.app )


		data_with_username_only = {'Username': 'jason@test.nextthought.com'}
		data_full = {'Username': 'jason@test.nextthought.com',
					 'password': 'password',
					 'email': 'foo@bar.com'	}

		path = b'/dataserver2/users/@@account.preflight.create'

		for data in (data_with_username_only, data_full):
			data = to_json_representation( data )
			res = app.post( path, data )

			assert_that( res, has_property( 'status_int', 200 ) )

class TestApplicationProfile(SharedApplicationTestBase):
	@WithSharedApplicationMockDS
	def test_preflight_user( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		app = TestApp( self.app )

		path = b'/dataserver2/users/sjohnson@nextthought.com/@@account.profile'

		res = app.get( path, extra_environ=self._make_extra_environ() )

		assert_that( res, has_property( 'status_int', 200 ) )
		assert_that( res.json_body, has_entry( 'ProfileSchema', has_key( 'opt_in_email_communication' ) ) )


def main(email=None, uname=None, cname=None):
	import sys
	_contact_email = email or sys.argv[1]
	_username = uname or sys.argv[2]
	child_name = cname or sys.argv[3]

	from zope import interface
	from zope.annotation.interfaces import IAttributeAnnotatable
	@interface.implementer(user_interfaces.IUserProfile,IAttributeAnnotatable)
	class FakeUser(object):
		username = _username
		contact_email = _contact_email
		realname = child_name

	class FakeEvent(object):
		request = True

	import nti.dataserver.utils
	from pyramid.testing import setUp as psetUp
	from pyramid.testing import tearDown as ptearDown
	from pyramid.testing import DummyRequest
	nti.dataserver.utils._configure( set_up_packages=('nti.appserver',) )
	request = DummyRequest()
	config = psetUp(registry=component.getGlobalSiteManager(),request=request,hook_zca=False)
	config.setup_registry()
	FakeEvent.request = request

	import pyramid_mailer
	from pyramid_mailer.interfaces import IMailer
	component.provideUtility( pyramid_mailer.Mailer.from_settings( {'mail.queue_path': '/tmp/ds_maildir' } ), IMailer )

	import nti.appserver.z3c_zpt
	from pyramid.interfaces import IRendererFactory
	component.provideUtility( nti.appserver.z3c_zpt.renderer_factory, IRendererFactory, name='.pt' )
	import nti.appserver.user_policies
	nti.appserver.user_policies.send_consent_request_on_new_coppa_account( FakeUser(), FakeEvent )

	import transaction
	transaction.commit()

if __name__ == '__main__':
	main()
