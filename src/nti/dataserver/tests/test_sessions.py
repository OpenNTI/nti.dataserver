#!/usr/bin/env python2.7
# disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that,  is_, none, is_not, has_property


from zope import component
from zope import interface

from nti.tests import verifiably_provides
import nti.dataserver.interfaces as nti_interfaces
import nti.dataserver.sessions as sessions

import mock_dataserver
from zope.deprecation import __show__


class MockSessionService(sessions.SessionService):

	def _spawn_cluster_listener(self):
		class PubSocket(object):
			def send_multipart( self, o ): pass
		self.pub_socket = PubSocket()
		return None

def test_session_cannot_change_owner():
	s = sessions.Session()
	assert_that( s, has_property( 'owner', none() ) )
	s.owner = 'me'
	assert_that( s, has_property( 'owner', 'me') )

	s.owner = 'me' # no change, allowed
	assert_that( s, has_property( 'owner', 'me') )

	try:
		s.owner = 'you' # not allowed
	except ValueError: pass
	else:
		assert_that( True, is_( False ), "Should raise ValueError" )

class TestSessionService(mock_dataserver.ConfiguringTestBase):

	def setUp(self):
		super(TestSessionService,self).setUp()
		self.session_service = MockSessionService()
		self.storage = sessions.SessionServiceStorage()
		component.provideUtility( self.storage, provides=nti_interfaces.ISessionServiceStorage )

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

			def put_server_msg( self, msg ): self.s_msg = msg
			def put_client_msg( self, msg ): self.c_msg = msg

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

	def test_create_session_deprecated(self):
		__show__.off()
		self.storage = sessions.SimpleSessionServiceStorage()
		component.provideUtility( self.storage, provides=nti_interfaces.ISessionServiceStorage )
		session = self.session_service.create_session( watch_session=False )
		assert_that( session, is_not( none() ) )
		assert_that( self.session_service.get_session( session.session_id ), is_( session ) )
		__show__.on()

	def test_create_session(self):
		session = self.session_service.create_session( watch_session=False )
		assert_that( session, is_not( none() ) )
		assert_that( self.session_service.get_session( session.session_id ), is_( session ) )
		assert_that( session, has_property( 'session_service', self.session_service ) )

	def test_get_dead_session(self):
		session = self.session_service.create_session( watch_session=False )
		assert_that( self.session_service.get_session( session.session_id ), is_( session ) )
		# connect it
		session.incr_hits()
		assert_that( session, has_property( 'connected', True ) )
		# kill it
		session.kill()
		assert_that( session, has_property( 'connected', False ) )

		# No longer able to get
		assert_that( self.session_service.get_session( session.session_id ), is_( none() ) )

	def test_get_by_owner(self):
		for _ in range(2): # multi times to create and modify datastructures
			session = self.session_service.create_session( watch_session=False )
			assert_that( self.session_service.get_session( session.session_id ), is_( session ) )
			assert_that( self.session_service.get_sessions_by_owner( 'me' ), is_( [] ) )

			session.owner = 'me'
			assert_that( self.session_service.get_sessions_by_owner( 'me' ), is_( [session] ) )

			# now dead
			session.incr_hits()
			session.kill()

			assert_that( self.session_service.get_sessions_by_owner( 'me' ), is_( [] ) )

	def test_delete_session(self):
		session = self.session_service.create_session( watch_session=False )
		session.owner = 'me' # give it an owner so its in the index

		self.session_service.delete_session( session.session_id )
		assert_that( self.session_service.get_session( session.session_id ), is_( none() ) )
		assert_that( self.session_service.get_sessions_by_owner( 'me' ), is_( [] ) )

		# Delete some foobar session
		self.session_service.delete_session( 42 )



def test_session_service_storage():
	assert_that( sessions.SessionServiceStorage(), verifiably_provides( nti_interfaces.ISessionServiceStorage ) )
