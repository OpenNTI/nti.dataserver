#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)
import six

import anyjson as json

import interfaces

from zope import interface
from zope import component

@interface.implementer(interfaces.ISocketIOSocket)
class SocketIOSocket(object):
	"""
	A socket is little more than a wrapper around a channel (pair of queues)
	and a way to format messages for those queues.
	"""

	# See: https://github.com/LearnBoost/socket.io-spec
	def __init__(self, channel, version="1"):
		"""
		:param channel: An :class:`interfaces.ISocketIOChannel`.
		"""
		self.channel = channel
		self.version = version

	@property
	def protocol(self):
		return component.getUtility( interfaces.ISocketIOProtocolFormatter, name=self.version )

	def send(self, message):
		self.channel.put_client_msg( message )

	def send_event(self, name, *args):
		self.send( self.protocol.make_event( name, *args ) )

	def send_heartbeat( self ):
		self.send( self.protocol.make_heartbeat( ) )

	def send_connect( self, data ):
		self.send( self.protocol.make_connect( data ) )

	def ack(self, msg_id, params):
		self.send( self.protocol.make_ack( msg_id, params ) )



class AbstractMessage(dict):
	interface.implements(interfaces.ISocketIOMessage)
	msg_type = -1
Message = AbstractMessage
# 'disconnect'
# 'connect'
# 'heartbeat'
# 'message'
# 'json'
# 'event'
# 'ack'
# 'error'
# 'noop'

class DisconnectMessage(AbstractMessage):
	msg_type = 0

class ConnectMessage(AbstractMessage):
	msg_type = 1

class HeartbeatMessage(AbstractMessage):
	msg_type = 2

class MessageMessage(AbstractMessage):
	msg_type = 3

class JsonMessage(AbstractMessage):
	msg_type = 4

class EventMessage(AbstractMessage):
	msg_type = 5

class AckMessage(AbstractMessage):
	msg_type = 6

class ErrorMessage(AbstractMessage):
	msg_type = 7

class NoopMessage(AbstractMessage):
	msg_type = 8



class SocketIOProtocolFormatter1(object):
	"""Parsing functions for version 1 of the socketio protocol."""

	interface.implements( interfaces.ISocketIOProtocolFormatter )

	_LIGHTWEIGHT_FRAME_DELIM      = b'\xff\xfd'     # u'\ufffd', the opening byte of a lightweight framing
	_LIGHTWEIGHT_FRAME_UTF8_DELIM = b'\xef\xbf\xbd' # utf-8 encoding of u'\ufffd'

	# See: https://github.com/LearnBoost/socket.io-spec
	def __init__(self):
		super(SocketIOProtocolFormatter1,self).__init__()

	def make_event(self, name, *args):
		if not name or not isinstance( name, six.string_types ) or name in self._reserved_event_names:
			raise ValueError( "Improper outgoing event name", name )
		return (b"5:::" + self.encode({'name': name, 'args': args})).encode('utf-8')

	def make_heartbeat( self ):
		return (b"2::")

	def make_noop( self ):
		return b"8::"

	def make_ack(self, msg_id, params):
		return (b"6:::%s%s" % (msg_id, self.encode(params))).encode('utf-8')

	def make_connect( self, tail=b'' ):
		return (b"1::%s" % tail).encode( 'utf-8' )

	def encode(self, message):
		if isinstance(message, six.string_types):
			return message

		if isinstance(message, (object, dict)):
			return self.encode(json.dumps(message))

		raise ValueError("Can't encode message")

	def _frame( self, msg ):
		"""
		Given a byte string message, frame it and return the framed bytes.
		"""
		if isinstance(msg,unicode):
			logger.warn( "Framing message that is unicode; should be bytes by this level %s", msg)
			msg = msg.encode('utf-8')
		return self._LIGHTWEIGHT_FRAME_UTF8_DELIM + str( len( msg ) ) + self._LIGHTWEIGHT_FRAME_UTF8_DELIM + msg

	def encode_multi( self, messages ):
		"""
		:param messages: A sequence of strings that have already been according
			to methods like :meth:`make_event`.
		:return: A byte string. If there was more than one message, this will be a framed
			string. Otherwise, it will be equivalent to the first object in messages.
		"""
		if messages is None or len(messages) == 0:
			# Hmm, nothing to do. Caller error?
			raise ValueError( "Invalid multi-message sequence." )

		if len(messages) == 1:
			msg = messages[0]
			if isinstance(msg,unicode):
				logger.warn( "Framing message that is unicode; should be bytes by this level %s", msg)
				msg = msg.encode('utf-8')
			return msg
		# Ok, we must frame them.
		framed = [self._frame(msg) for msg in messages]
		return b''.join( framed )


	def _parse_data( self, data ):
		data = data.lstrip()
		return json.loads( data )

	# 0 to 5 are all we handle
	_known_messages = [str(i) for i in range(6)]
	_reserved_event_names = ('message', 'connect', 'disconnect', 'open',
							 'close', 'error', 'retry', 'reconnect')

	def decode(self, data):
		"""
		:return: A single Message object.
		"""

		if not data:
			raise ValueError( "Must provide data" )

		if data[0] not in self._known_messages:
			ve = ValueError( 'Unknown message type', data )
			ve.message = 'Unknown message type'
			raise ve

		msg_type, msg_id, tail = data.split(":", 2)

		# 'disconnect'
		# 'connect'
		# 'heartbeat'
		# 'message'
		# 'json'
		# 'event'
		# 'ack'
		# 'error' -- not handled
		# 'noop'  -- not handled


		if msg_type == "0": # disconnect
			return DisconnectMessage()

		if msg_type == "1": # connect
			return ConnectMessage( data=tail )


		if msg_type == "2": # heartbeat
			return HeartbeatMessage()


		message = None
		msg_endpoint, data = tail.split(":", 1)
		assert msg_endpoint is not None

		data = data.decode( 'utf-8', 'replace' )
		if msg_type == "3": # message
			message = MessageMessage(
				type='message',
				data=data )
		elif msg_type == "4": # json
			message = self._parse_data(data)
			message = JsonMessage(message)
		elif msg_type == "5": # event
			message = self._parse_data(data)
			message = EventMessage( message )

			if 'name' not in message:
				raise ValueError( 'Improper event, missing name', message )
			if message['name'] in self._reserved_event_names:
				raise ValueError( 'Improper event, reserved name', message )
			if not isinstance( message.get( 'args' ), list ):
				raise ValueError( 'Improper event, missing args', message )

			if "+" in msg_id:
				message['id'] = msg_id
			else:
				pass # TODO send auto ack
			message['type'] = 'event'

		assert message is not None, "Got unhandled message"

		return message

	def decode_multi( self, data ):
		"""
		:return: A sequence of Message objects
		"""
		DELIM1 = self._LIGHTWEIGHT_FRAME_DELIM
		DELIM2 = self._LIGHTWEIGHT_FRAME_UTF8_DELIM

		# If they give us a unicode object (weird!)
		# encode as bytes in utf-8 format
		if isinstance( data, unicode ):
			data = data.encode( 'utf-8' )
		assert isinstance( data, str ), "Must be a bytes object, not unicode"

		if not data.startswith( DELIM1 ) and not data.startswith( DELIM2 ):
			# Assume one
			return ( self.decode( data ), )

		d = DELIM1
		dl = 2
		if data.startswith( DELIM2 ):
			d = DELIM2
			dl = 3

		messages = []
		start = 0
		while start + dl < len(data):
			start_search = start + dl
			end = data.find( d, start_search )
			len_str = int( data[start_search:end] )
			if len_str <= 0: raise ValueError( 'Bad length' )
			end_data = end + dl + len_str
			sub_data = data[end+dl:end_data]
			if not sub_data: raise ValueError( "Data from %s to %s was not len %s (got %s)" % (start_search, end_data, len_str, sub_data ) )
			if not len(sub_data) == len_str: raise ValueError( "Data from %s to %s was not len %s (got %s)" % (start_search, end_data, len_str, sub_data ) )
			messages.append( self.decode( sub_data ) )

			start = end_data

		return messages
