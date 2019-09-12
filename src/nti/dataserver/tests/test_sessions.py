#!/usr/bin/env python2.7

from __future__ import unicode_literals, absolute_import, print_function

# disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that,  is_, none, is_not, has_property
from hamcrest import has_length
from hamcrest import contains

import sys
import time
import transaction

from nose.tools import assert_raises

from zope import component

from nti.testing.matchers import validly_provides as verifiably_provides
import nti.dataserver.interfaces as nti_interfaces
from nti.socketio import interfaces as sio_interfaces
import nti.dataserver.sessions as sessions
from nti.dataserver import session_storage
from nti.dataserver import users

from nti.dataserver.interfaces import IRedisClient

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

class MockSessionService(sessions.SessionService):

	def __init__( self ):
		super(MockSessionService,self).__init__()
		self.created_users = []

	def _spawn_cluster_listener(self):
		return None

	default_owner = 'sjohnson@nti'

	def create_session( self, *args, **kwargs ):
		if 'owner' not in kwargs:
			kwargs['owner'] = self.default_owner
			if users.User.get_user( kwargs['owner'] ) is None:
				created = users.User.create_user( username=kwargs['owner'] )
				self.created_users.append( created )

		return sessions.SessionService.create_session( self, *args, **kwargs )


class TestSessionService(mock_dataserver.DataserverLayerTest):


	def setUp(self):
		super(TestSessionService,self).setUp()
		self.session_service = MockSessionService()
		self.storage = session_storage.OwnerBasedAnnotationSessionServiceStorage()
		component.provideUtility( self.storage, provides=nti_interfaces.ISessionServiceStorage )

	def test_session_cannot_change_owner(self):
		s = sessions.Session()
		assert_that( s, has_property( 'owner', none() ) )
		with assert_raises( AttributeError ):
			s.owner = 'me'
			# Must be assigned at creation time


	def test_get_set_proxy_session(self):
		self.session_service.set_proxy_session( '1', self )
		assert_that( self.session_service.get_proxy_session( '1' ), is_( self ) )
		self.session_service.set_proxy_session( '1' )
		assert_that( self.session_service.get_proxy_session( '1' ), is_( none() ) )

	def test_dispatch_to_proxy(self):
		class Proxy(object):
			value = None
			def has_one(self, one_arg):
				self.value = one_arg

			s_msg = object()
			c_msg = object()

			def queue_message_from_client( self, msg ): self.s_msg = msg
			def queue_message_to_client( self, msg ): self.c_msg = msg

		proxy = Proxy()
		assert_that( proxy, has_property( 's_msg', is_not( none() ) ) )
		assert_that( proxy, has_property( 'c_msg', is_not( none() ) ) )

		self.session_service.set_proxy_session( '1', proxy )
		handled = self.session_service._dispatch_message_to_proxy( '1', 'has_one', self )
		assert_that( handled, is_( True ) )
		assert_that( proxy, has_property( 'value', self ) )

		handled = self.session_service._dispatch_message_to_proxy( '1', 'missing', 2 )
		assert_that( handled, is_( False ) )

		# The session dead method is handled specially
		self.session_service._dispatch_message_to_proxy( '1', 'session_dead', "ignored" )
		assert_that( proxy, has_property( 's_msg', none() ) )
		assert_that( proxy, has_property( 'c_msg', none() ) )


	@WithMockDSTrans
	def test_create_delete_session(self):
		session = self.session_service.create_session( watch_session=False )
		assert_that( session, is_not( none() ) )
		assert_that( self.session_service.get_session( session.session_id ), is_( session ) )

		# If we delete the user, the sessions are no longer accessible
		assert_that( self.session_service.created_users, has_length( 1 ) )
		assert_that( self.session_service.created_users[0], has_property( 'username', session.owner ) )

		deleted_user = users.User.delete_user( session.owner )
		assert_that( deleted_user, is_( self.session_service.created_users[0] ) )

		assert_that( self.session_service.get_session( session.session_id ), is_( none() ) )

	@WithMockDSTrans
	def test_queue_messages_to_session(self):
		session = self.session_service.create_session( watch_session=False )
		assert_that( session, is_not( none() ) )
		assert_that( self.session_service.get_session( session.session_id ), is_( session ) )

		self.session_service.queue_message_from_client( session.session_id, b'foobar' )
		self.session_service.queue_message_to_client( session.session_id, b'foobar' )

		transaction.commit()
		transaction.begin()
		to_client = list(self.session_service.get_messages_to_client( session.session_id ))
		from_client = list(self.session_service.get_messages_from_client( session.session_id ))

		for l in to_client, from_client:
			assert_that( l, has_length( 1 ) )
			assert_that( l, contains( 'foobar' ) )

	@WithMockDSTrans
	def test_clear_disconnect_timeout(self):
		session = self.session_service.create_session( watch_session=False )
		assert_that( session, is_not( none() ) )

		self.session_service.clear_disconnect_timeout( session.session_id, 42 )
		assert_that( self.session_service.get_last_heartbeat_time( session.session_id ), is_( 42 ) )


	@WithMockDSTrans
	def test_get_dead_session(self):
		redis = component.getUtility(IRedisClient)
		session = self.session_service.create_session( watch_session=False )
		assert_that( self.session_service.get_session( session.session_id ), is_( session ) )
		# connect it
		session.connection_confirmed = True # Needed to get the event
		session.incr_hits()
		assert_that( session, has_property( 'connected', True ) )
		# This should have a stat now
		assert_that( redis.zrange(sessions._session_active_keys, 0, -1, withscores=True),
					 is_( [(session.owner, 1)]) )
		# kill it
		session.kill()
		assert_that( session, has_property( 'connected', False ) )

		# No longer able to get
		assert_that( self.session_service.get_session( session.session_id ), is_( none() ) )
		# And the stat is 0
		assert_that( redis.zrange(sessions._session_active_keys, 0, -1, withscores=True),
					 is_( [(session.owner, 0)]) )

	@WithMockDSTrans
	def test_get_by_owner(self):
		for _ in range(2): # multi times to create and modify datastructures
			session = self.session_service.create_session( watch_session=False )
			assert_that( self.session_service.get_session( session.session_id ), is_( session ) )
			assert_that( self.session_service.get_sessions_by_owner( session.owner ), is_( [session] ) )

			# now dead
			session.incr_hits()
			session.kill()

			assert_that( self.session_service.get_sessions_by_owner( session.owner ), is_( [] ) )

	@WithMockDSTrans
	def test_many_dead_sessions_broadcast_doesnt_overflow(self):
		"Having to clean up and notify() that many sessions are dead doesn't cause a stack overflow."

		called = [0]
		@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionDisconnectedEvent )
		def session_disconnected_broadcaster( session, event ):
			# Emulate what the real listener does, which is ask for other sessions for the user
			self.session_service.get_sessions_by_owner( session.owner )
			called[0] += 1

		component.provideHandler( session_disconnected_broadcaster )

		sessions = []
		recur_limit = sys.getrecursionlimit()
		# The length needs to be pretty big to ensure recursion fails
		two_days_ago = time.time() - 60 * 60 * 24 * 2
		for val in range(recur_limit * 2):
			session = self.session_service.create_session( watch_session=False, drop_old_sessions=False )
			if val % 2 == 0:
				# Make every other value a day+ old, so it gets cleaned up.
				session.creation_time -= two_days_ago
			sessions.append( session )
			session.incr_hits()

		# Only half are alive now.
		assert_that( self.session_service.get_sessions_by_owner( session.owner ),
					 has_length( len( sessions ) / 2 ) )
		assert_that( called[0], is_( len( sessions ) / 2 ) )

		# Now kill the rest of them, silently
		for session in sessions:
			session.creation_time = 0
			del session.last_heartbeat_time

		# Now we can request them again, get nothing, and not overflow the stack doing so.
		assert_that( self.session_service.get_sessions_by_owner( session.owner ), is_( [] ) )
		assert_that( called[0], is_( len( sessions ) ) )

	@WithMockDSTrans
	def test_delete_session(self):
		session = self.session_service.create_session( watch_session=False )

		self.session_service.delete_session( session.session_id )
		assert_that( self.session_service.get_session( session.session_id ), is_( none() ) )
		assert_that( self.session_service.get_sessions_by_owner( session.owner ), is_( [] ) )

		# Delete some foobar session
		self.session_service.delete_session( 42 )

	def test_session_service_storage(self):
		assert_that( session_storage.OwnerBasedAnnotationSessionServiceStorage(), verifiably_provides( nti_interfaces.ISessionServiceStorage ) )


