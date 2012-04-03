#!/usr/bin/env python
#pylint: disable=R0904
from __future__ import unicode_literals

from nti.tests import verifiably_provides, AbstractTestBase
from nti.socketio import protocol
from nti.socketio import interfaces

from hamcrest import assert_that, is_, has_entry, has_length

def test_protocol_provides():
	assert_that( protocol.SocketIOSocket( None ), verifiably_provides( interfaces.ISocketIOSocket ) )

class TestSocketIOProtocolFormatter1(AbstractTestBase):

	def setUp(self):
		self.protocol = protocol.SocketIOProtocolFormatter1()

	def test_makes_return_bytes(self):
		assert_that( self.protocol.make_event( 'name' ), is_( str ) )
		assert_that( self.protocol.make_heartbeat(), is_( str ) )
		assert_that( self.protocol.make_ack( '1', [] ), is_( str ) )
		assert_that( self.protocol.make_connect( '' ), is_( str ) )


	def test_decode_disconnect( self ):
		assert_that( self.protocol.decode( '0::' ),
					 is_( protocol.DisconnectMessage ) )
		assert_that( self.protocol.decode( b'0::' ),
					 is_( protocol.DisconnectMessage ) )

	def test_decode_connect( self ):
		for s in (u'1::tail',b'1::tail'):
			msg = self.protocol.decode( s )
			assert_that( msg, is_( protocol.ConnectMessage ) )
			assert_that( msg, has_entry( 'data', 'tail' ) )

	def test_decode_heartbeat( self ):
		for s in (u'2::tail',b'2::tail'):
			msg = self.protocol.decode( s )
			assert_that( msg, is_( protocol.HeartbeatMessage ) )
			assert_that( msg, has_length( 0 ) )

	def test_decode_message( self ):
		for s in ( u'3:::data',b'3:::data' ):
			msg = self.protocol.decode( s )
			assert_that( msg, is_( protocol.MessageMessage ) )
			assert_that( msg, has_entry( 'data', 'data' ) )

	def test_decode_json( self ):
		for decoder in (self.protocol.decode, lambda x: self.protocol.decode_multi(x)[0]):
			for s in ( u'4:::{}', b'4:::{}' ):
				msg = decoder( s )
				assert_that( msg, is_( protocol.JsonMessage ) )
				assert_that( msg, has_length(  0 ) )

	def test_decode_event( self ):
		for decoder in (self.protocol.decode, lambda x: self.protocol.decode_multi(x)[0]):
			for s in ( u'5:::{"name": "foo"}',b'5:::{"name": "foo"}' ):
				msg = decoder( s )
				assert_that( msg, is_( protocol.EventMessage ) )
				assert_that( msg, has_entry( 'type', 'event' ) )
				assert_that( msg, has_entry( 'name', 'foo' ) )
				assert_that( msg, has_length( 2 ) )

			for s in ( u'5:1+::{"name": "foo"}',b'5:1+::{"name": "foo"}' ):
				msg = decoder( s )
				assert_that( msg, is_( protocol.EventMessage ) )
				assert_that( msg, has_entry( 'type', 'event' ) )
				assert_that( msg, has_entry( 'name', 'foo' ) )
				assert_that( msg, has_length( 3 ) )
				assert_that( msg, has_entry( 'id', '1+' ) )

	def test_decode_exceptions( self ):
		with self.assertRaises( ValueError ) as cm:
			self.protocol.decode( '' )

		assert_that( cm.exception.message, is_( 'Must provide data' ) )

		with self.assertRaises( ValueError ) as cm:
			self.protocol.decode( '9' )
		assert_that( cm.exception.message, is_( 'Unknown message type' ) )
		assert_that( cm.exception.args, is_( ('Unknown message type', '9') ) )


	def test_decode_multi( self ):
		ucode = u'5:1+::{"name": "foo"}'
		unicode_framed = u'\ufffd' + unicode(len( ucode )) + u'\ufffd' + ucode

		def decode( framed ):
			msgs = self.protocol.decode_multi( framed )

			assert_that( msgs, has_length( 1 ) )
			msg = msgs[0]
			assert_that( msg, is_( protocol.EventMessage ) )
			assert_that( msg, has_entry( 'name', 'foo' ) )

		decode( unicode_framed )

		bts = b'5:1+::{"name": "foo"}'
		byte_framed = b'\xef\xbf\xbd' + str(len( bts )) + b'\xef\xbf\xbd' + bts
		decode( byte_framed )

		# Too short a length
		with self.assertRaises( ValueError ):
			byte_framed = b'\xef\xbf\xbd' + b'5' + b'\xef\xbf\xbd' + bts
			decode( byte_framed )

		# Too long a length
		with self.assertRaises( ValueError ):
			byte_framed = b'\xef\xbf\xbd' + str(len( bts ) + 5) + b'\xef\xbf\xbd' + bts
			decode( byte_framed )
