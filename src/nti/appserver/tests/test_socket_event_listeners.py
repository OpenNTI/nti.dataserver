#!/usr/bin/env python2.7
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that, is_

from nti.dataserver import interfaces as nti_interfaces, users
from nti.chatserver import interfaces as chat_interfaces

from nti.appserver.tests import ConfiguringTestBase
from nti.dataserver.tests import mock_dataserver

from zope import interface
from zope import component

from nti.appserver._socket_event_listeners import session_disconnected_broadcaster, session_connected_broadcaster, _notify_friends_of_presence
from nti.appserver._socket_event_listeners import user_change_broadcaster


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

class TestBroadcasts(ConfiguringTestBase):

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
