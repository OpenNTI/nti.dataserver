#!/usr/bin/env python
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that, is_
from hamcrest import has_length
from hamcrest import none
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_property
from hamcrest import contains_string

from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.chatserver.presenceinfo import PresenceInfo

from nti.appserver.tests import ITestMailDelivery
from nti.dataserver.tests import mock_dataserver

from nti.app.testing.layers import NewRequestLayerTest

from zope import interface
from zope import component

from nti.appserver._socket_event_listeners import session_disconnected_broadcaster
from nti.appserver._socket_event_listeners import send_presence_when_contact_added
from nti.appserver._socket_event_listeners import  _notify_friends_of_presence

from nti.appserver._stream_event_listeners import user_change_broadcaster
from nti.appserver._stream_event_listeners import user_change_new_note_emailer, TemporaryChangeEmailMarker, ITemporaryChangeEmailMarker

class MockChatserver(object):
	interface.implements(chat_interfaces.IChatserver)


class MockSessionManager(object):

	session_list = ()
	def get_sessions_by_owner(self,username):
		return self.session_list
	pchange = ()
	def send_event_to_user( self, *args ):
		self.pchange = args

	presence_list = ()
	def getPresenceOfUsers( self, userlist ):
		return self.presence_list

class MockSession(object):
	owner = None

@interface.implementer(nti_interfaces.IStreamChangeEvent)
class MockChange(object):
	type = "Type"
	object = None
	send_change_notice = True

class TestEvents(NewRequestLayerTest):

	def test_without_components(self):
		session_disconnected_broadcaster( None, None )
		_notify_friends_of_presence( None, None )

	@mock_dataserver.WithMockDSTrans
	def test_broadcast(self):
		cs = MockSessionManager()

		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		user2 = users.User.create_user( self.ds, username='sjohnson2@nextthought.com' )
		user.follow( user2 )

		session = MockSession()
		session.owner = user.username

		# With no session manager, nothing happens
		session_disconnected_broadcaster( session, None )
		assert_that( cs.pchange, is_( () ) )

		self.ds.session_manager = cs
		session_disconnected_broadcaster( session, None )
		assert_that( cs.pchange, contains( user2.username,
										   'chat_setPresenceOfUsersTo', # name
										   has_entry( user.username, has_property( 'type', 'unavailable' ) ) ))



		change = MockChange()
		user_change_broadcaster( user, change )
		assert_that( cs.pchange, is_( (user.username, 'data_noticeIncomingChange', change) ) )

		cs.session_list = [session]
		cs.presence_list = ( PresenceInfo( type='available' ), )
		self.ds.chatserver = cs
		evt = chat_interfaces.ContactISubscribeToAddedToContactsEvent( user, user2 )
		send_presence_when_contact_added( user, evt )
		assert_that( cs.pchange, contains( user2.username,
										   'chat_setPresenceOfUsersTo', # name
										   has_entry( user.username, has_property( 'type', 'available' ) ) ))

	@mock_dataserver.WithMockDSTrans
	def test_email(self):
		# Remove the default
		def_marker = component.getUtility( ITemporaryChangeEmailMarker )
		component.getGlobalSiteManager().unregisterUtility( def_marker, provided=ITemporaryChangeEmailMarker, name='' )
		assert_that( component.queryUtility( ITemporaryChangeEmailMarker, name='' ), is_( none() ) )
		mailer = component.getUtility( ITestMailDelivery )
		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )

		# With no note, email address or marker, nothing happens
		change = MockChange()
		# wrong type
		user_change_new_note_emailer( user, change )
		assert_that( mailer.queue, has_length( 0 ) )

		change.type = nti_interfaces.SC_CREATED
		change.creator = user
		user_change_new_note_emailer( user, change )
		# Wrong object
		assert_that( mailer.queue, has_length( 0 ) )

		change.object = MockSession()
		change.object.title = 'My Title'
		interface.alsoProvides( change.object, nti_interfaces.INote )
		user_change_new_note_emailer( user, change )
		# no email
		assert_that( mailer.queue, has_length( 0 ) )

		profile = user_interfaces.IUserProfile( user )
		profile.email = 'jason.madden@nextthought.com'
		profile.opt_in_email_communication = True
		profile.realname = 'Steve'

		user_change_new_note_emailer( user, change )
		# yes email, but no utility
		assert_that( mailer.queue, has_length( 0 ) )

		component.provideUtility( TemporaryChangeEmailMarker(), name=user.username )

		change.object.body = [u"Plain text", object(), u"More plain text"]
		change.object.creator = user
		user_change_new_note_emailer( user, change )
		# yes email, and yes utility
		assert_that( mailer.queue, has_length( 1 ) )

		msg = mailer.queue[0]
		assert_that( msg, has_property( 'subject', 'Steve created a MockSession: "My Title"') )
		assert_that( msg, has_property( 'body', contains_string( "Plain" ) ) )
