#!/usr/bin/env python2.7
"""Interfaces supporting socket.io"""
from __future__ import unicode_literals
from zope import interface, schema
#pylint: disable=E0213,E0211

_writer_base = interface.Interface
_reader_base = interface.Interface
_socket_base = None


class ISocketIOMessage(interface.Interface):
	"""
	A message read or written to socket io.
	"""
	msg_type = schema.Int(
		description="The numeric value of the message type, from 0 to 8",
		readonly=True )

class ISocketIOProtocolFormatter(interface.Interface):
	"""
	Functions for formatting messages appropriately for socket io.
	"""

	def make_event(name, *args):
		"""
		"""

	def make_heartbeat( ):
		""" """

	def make_noop():
		"""
		"""

	def make_ack(msg_id, params):
		""" """

	def make_connect( data ):
		"""
		"""

	def decode(data):
		"""
		:return: A single :class:`ISocketIOMessage` object.
		"""

	def decode_multi( data ):
		"""
		:return: A sequence of Message objects
		"""

	def encode_multi( messages ):
		"""
		:param messages: A sequence of strings that have already been according
			to methods like :meth:`make_event`.
		:return: A byte string. If there was more than one message, this will be a framed
			string. Otherwise, it will be equivalent to the first object in messages.
		"""

class ISocketIOWriter(_writer_base):
	"""
	Defines the write-side of a socket (the ability to send messages to a client)
	"""

	# externalize_function = schema.Field(
	# 	description="The function used to externalize data to send to the client. Defaults to creating strings of JSON.",
	# 	readonly=True)

	def ack( msg_id, params ):
		"""
		Sends an acknowledgment to a previously received message.
		This is the socket.io "client-handled" acknowledgement and is delivered
		to the waiting client callback.

		:param msg_id: The message ID to acknowledge. Arrived as the `id` field
			of an incoming message.
		:param params: The data to send with the acknowledgement. Will be externalized
			to a string.
		"""

	def send( message ):
		"""
		Sends arbitrary message data to the connected client, or another client.

		:param message: The exact string of data to send. In general, this
			method should not be invoked by clients.
		"""

	def send_event( name, *args ):
		"""
		Sends a named event with structured arguments to the connected client.

		:param string name: The name of the event to send.
		:param args: The arguments the client's event handler should get, in order.
			Will be externalized to strings using the externalize_function.
		"""



class ISocketIOReader(_reader_base):
	"""
	The read-side of a socket to a connected client.
	"""

	# def receive():
	# 	"""
	# 	Waits for an incoming message and returns it.
	# 	"""

class ISocketIOSocket(ISocketIOReader,ISocketIOWriter):
	"""
	A socket to a connected client that can be used to read and write messages.
	"""

class ISocketIOTransport(interface.Interface):
	"""
	The low-level interface that handles sending and receiving messages.
	An :class:`ISocketIOSocket` may have many different transports over its
	lifetime.
	"""

	def connect( session, request_method ):
		"""
		Given a (newly-created) session and a WSGI request, connect the session
		to this transport.

		This method may be called to reconnect an already established session
		to a different transport during transport fallback.

		:return: This may return an iterable of greenlets; if so, then they must be joined
			on for the transport to run to completion before the WSGI request completes. It may instead return an
			:class:`pyramid.interfaces.IResponse` if the transport is synchronous, and that
			response is the value to be immediately returned to the client, terminating the
			WSGI request.
		"""


	def kill():
		"""
		Requests that this transport terminate any ongoing communication.
		"""

class ISocketIOChannel(interface.Interface):
	"""
	Something that represents a queued connection between client
	and server. A channel is a bidirectional stream of messages; no interpretation
	of the messages is done (the messages are strings of bytes).
	"""

	def put_server_msg( msg ):
		"""
		A message, ``msg``, has arrived at the server and is ready to
		be processed.
		"""

	def put_client_msg( msg ):
		"""
		A message, ``msg``, is ready to be sent to the remote client.
		"""

class ISocketSession(ISocketIOChannel):
	"A higher-level abstraction on top of io channels."

	connected = schema.Bool(title=u'Is the session known to be connected to a client?')
	owner = schema.TextLine(title=u'The name of the user that owns this session.')

	def heartbeat():
		pass
	def kill():
		pass

class ISocketSessionEvent(interface.interfaces.IObjectEvent):
	"""
	An event fired relating to a socket session.
	In general, socket events will only be fired for sockets that have owners.
	"""

class ISocketSessionConnectedEvent(interface.interfaces.IObjectEvent):
	"""
	An event that is fired when a socket session establishes a connection for the first time.
	"""

class ISocketSessionDisconnectedEvent(ISocketSessionEvent):
	"""
	An event that is fired when a socket session disconnects.
	"""

class SocketSessionEvent(interface.interfaces.ObjectEvent):
	interface.implements(ISocketSessionEvent)

class SocketSessionConnectedEvent(SocketSessionEvent):
	interface.implements(ISocketSessionConnectedEvent)

class SocketSessionDisconnectedEvent(SocketSessionEvent):
	interface.implements(ISocketSessionDisconnectedEvent)

class ISocketEventHandler(interface.Interface):
	"""
	Interface for things that want to handle socket
	events received from a connected user.

	The general contract for these objects is that they will have
	public methods corresponding to the events they wish to handle from
	the user. If the method returns a result that is not None, then if the
	user requested acknowledgement that result will be sent as the ack (if
	the user requested ack and the result was None, False will be returned).

	These objects may be registered as subscription adapters for
	:class:`socketio.interfaces.ISocketIOSocket`. If there is duplication
	among the handlers for a particular event, all will be called in no
	defined order; the last non-None result will be used for ack.
	"""

	event_prefix = schema.Field(
		title=u'If present, names the prefix which should be subtracted from all incoming events before searching for a handler.',
		description=u'For example, a prefix of chat and a method name of handle would match an event chat_handle',
		required=False )
