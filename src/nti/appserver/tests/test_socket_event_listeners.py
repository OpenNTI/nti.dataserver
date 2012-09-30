#!/usr/bin/env python
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that, is_
from hamcrest import has_length
from hamcrest import none

from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces

from nti.appserver.tests import ConfiguringTestBase, ITestMailDelivery
from nti.dataserver.tests import mock_dataserver

from zope import interface
from zope import component

from nti.appserver._socket_event_listeners import session_disconnected_broadcaster, session_connected_broadcaster, _notify_friends_of_presence

from nti.appserver._stream_event_listeners import user_change_broadcaster
from nti.appserver._stream_event_listeners import user_change_new_note_emailer, TemporaryChangeEmailMarker, ITemporaryChangeEmailMarker

class MockChatserver(object):
	interface.implements(chat_interfaces.IChatserver)

	pchange = ()
	def send_event_to_user( self, *args ):
		self.pchange = args

class MockSessionManager(object):

	def get_sessions_by_owner(self,username):
		return ()

class MockSession(object):
	owner = None

class MockChange(object):
	type = "Type"
	object = None

class TestEvents(ConfiguringTestBase):

	def test_without_components(self):
		session_disconnected_broadcaster( None, None )
		_notify_friends_of_presence( None, None )

	@mock_dataserver.WithMockDSTrans
	def test_broadcast(self):
		cs = MockChatserver()
		component.provideUtility( cs )

		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		user2 = users.User.create_user( self.ds, username='sjohnson2@nextthought.com' )
		user.follow( user2 )

		session = MockSession()
		session.owner = user.username

		# With no session manager, nothing happens
		session_disconnected_broadcaster( session, None )
		assert_that( cs.pchange, is_( () ) )

		self.ds.session_manager = MockSessionManager()
		session_disconnected_broadcaster( session, None )
		assert_that( cs.pchange, is_( (user2.username, 'chat_presenceOfUserChangedTo', user.username, 'Offline') ))

		session_connected_broadcaster( session, None )
		assert_that( cs.pchange, is_( (user2.username, 'chat_presenceOfUserChangedTo', user.username, 'Online') ))

		change = MockChange()
		user_change_broadcaster( user, change )
		assert_that( cs.pchange, is_( (user.username, 'data_noticeIncomingChange', change) ) )

		assert_that( component.getGlobalSiteManager().unregisterUtility( cs ), is_( True ) )

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
		user_change_new_note_emailer( user, change )
		# Wrong object
		assert_that( mailer.queue, has_length( 0 ) )

		change.object = MockSession()
		interface.alsoProvides( change.object, nti_interfaces.INote )
		user_change_new_note_emailer( user, change )
		# no email
		assert_that( mailer.queue, has_length( 0 ) )

		profile = user_interfaces.IUserProfile( user )
		profile.email = 'jason.madden@nextthought.com'
		profile.opt_in_email_communication = True

		user_change_new_note_emailer( user, change )
		# yes email, but no utility
		assert_that( mailer.queue, has_length( 0 ) )

		component.provideUtility( TemporaryChangeEmailMarker(), name=user.username )

		change.object.body = [u"Plain text", object(), u"More plain text"]
		change.object.creator = user
		user_change_new_note_emailer( user, change )
		# yes email, and yes utility
		assert_that( mailer.queue, has_length( 1 ) )
