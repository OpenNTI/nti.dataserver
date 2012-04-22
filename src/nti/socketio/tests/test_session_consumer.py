#!/usr/bin/env python2.7
# disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that,  is_, contains, has_entry, has_item
from nti.dataserver.tests import has_attr

from zope import component
from zope import interface

import nti.dataserver.users as users
import nti.dataserver.interfaces as nti_interfaces
import nti.chatserver.interfaces as chat_interfaces
from nti.chatserver import _handler as chat_handler, messageinfo

from nti.socketio.session_consumer import SessionConsumer, UnauthenticatedSessionError


import nti.socketio as socketio
import nti.socketio.protocol
from nti.dataserver.tests import mock_dataserver

class MockSocketIO(object):

	def __init__( self ):
		# verification
		self.events = []
		self.data = []
		self.acks = []
		self.args = None
		# mocking
		self.session = self
		self.session_id = 'MockSessionId'
		self.owner = 'MockOwner'
		self.handler = None
		self.internalize_function = None

	def send_event( self, name, *args ):
		socketio.protocol.SocketIOProtocolFormatter1().make_event( name, *args )
		self.events.append( (name, args) )

	def send( self, data ):
		self.data.append( data )

	def ack( self, mid, data ):
		socketio.protocol.SocketIOProtocolFormatter1().make_ack( mid, data )
		self.acks.append( (mid,data) )

	def new_protocol( self, h=None ): return self
	socket = property(new_protocol)
	def incr_hits(self): pass

class TestSessionConsumer(mock_dataserver.ConfiguringTestBase):
	cons = None
	handler = None
	socket = None

	def setUp(self):
		super(TestSessionConsumer,self).setUp()
		self.cons = SessionConsumer()
		self.evt_handlers = {'chat': [self]}
		self.cons._create_event_handlers = lambda *args: self.evt_handlers
		self.socket = MockSocketIO()

	def test_bad_messages(self):
		assert_that( self.cons( self.socket, None ), # Socket death
					 is_( False ) )
		assert_that( self.cons( self.socket, {} ), # Non-'event'
					 is_( False ) )
		assert_that( self.cons( self.socket, {'type': 'event'} ), # unhandled
					 is_( False ) )

	def test_unauth_session(self):
		self.socket.owner = None
		with self.assertRaises(UnauthenticatedSessionError):
			self.cons( self.socket, None )

	def test_create_event_handlers(self):
		# There's no IChatserver registered, so this is all you get
		interface.alsoProvides( self.socket, socketio.interfaces.ISocketIOSocket )
		class MockChat(object):
			interface.implements( nti_interfaces.ISocketEventHandler )
			component.adapts( socketio.interfaces.ISocketIOSocket )

			def __init__( self, sock ):
				self.socket = sock

		class MockChatServer(object): pass
		o = MockChatServer()
		interface.directlyProvides( o, chat_interfaces.IChatserver)
		component.provideUtility( o )

		component.provideSubscriptionAdapter( MockChat )

		del self.cons._create_event_handlers
		handlers = self.cons._create_event_handlers( self.socket )
		assert_that( handlers, has_entry( '', has_item(is_(MockChat)) ) )

		MockChat.event_prefix = 'chat'
		handlers = self.cons._create_event_handlers( self.socket )
		assert_that( handlers, has_entry( 'chat', has_item(is_(MockChat)) ) )

		component.getGlobalSiteManager().unregisterUtility( o )



	def _auth_user(self):
		users.User.create_user( self.ds, username='foo@bar' )
		# self.cons._username = 'foo@bar'
		# self.cons._initialize_session( self.socket.session )


		# assert_that( self.cons, has_attr( '_username', 'foo@bar') )
		# assert_that( self.cons, has_attr( '_event_handlers', has_entry( 'chat', [self] ) ) )

	@mock_dataserver.WithMockDSTrans
	def test_auth_user(self):
		self._auth_user()

	def test_kill(self):
		class X(object): pass

		class Y(object):
			destroyed = False
			def destroy(self): self.destroyed = True
		y = Y()
		self.evt_handlers = { 'chat': [X()], 'y': [y] }


		self.cons.kill(self.socket)
		assert_that( y, has_attr( 'destroyed', True ) )

	@mock_dataserver.WithMockDSTrans
	def test_send_non_default_input_data( self ):
		# Authenticate
		self._auth_user()

		class X(object):
			im_class = None
			obj = None
			theEvent = None
		x = X()
		# Make the event handler look like a bound
		# method of another class
		def theEvent( obj ):
			x.obj = obj
		theEvent.im_class = chat_handler._ChatHandler
		x.theEvent = theEvent
		self.evt_handlers['chat'] = [x]
		self.cons( self.socket, {'type': 'event',
								 'name': 'chat_theEvent',
								 'args': ({ 'Class': 'MessageInfo' },) } )

		assert_that( x.obj, is_( messageinfo.MessageInfo ) )

	@mock_dataserver.WithMockDSTrans
	def test_namespace_event( self ):
		# Authenticate
		self._auth_user()

		# Dispatch chat event
		def h( arg):
			self.socket.args = arg
		self.handler = h
		self.cons( self.socket, {'type': 'event', 'name': 'chat_handler', 'args': ("The arg",)} )

		assert_that( self.socket, has_attr( 'args', 'The arg') )

	@mock_dataserver.WithMockDSTrans
	def test_ack_event( self ):
		# Authenticate
		self._auth_user()

		# Dispatch chat event
		def h( arg):
			self.socket.args = arg
			return "The result"

		self.handler = h
		self.cons( self.socket, {'id': "1", 'type': 'event', 'name': 'chat_handler', 'args': ("The arg",)} )

		assert_that( self.socket, has_attr( 'args', 'The arg') )
		assert_that( self.socket.acks, contains( ('1', ["The result"])) )

	@mock_dataserver.WithMockDSTrans
	def test_exception_event( self ):
		# Authenticate
		self._auth_user()

		# Dispatch chat event
		def h( arg):
			raise Exception( "The error" )

		self.handler = h
		self.cons( self.socket, {'type': 'event', 'name': 'chat_handler', 'args': ("The arg",)} )

		assert_that( self.socket.events, contains( ('server-error', ("The error",))) )
