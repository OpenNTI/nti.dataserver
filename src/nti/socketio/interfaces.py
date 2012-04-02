#!/usr/bin/env python2.7
"""Interfaces supporting socket.io"""
from __future__ import unicode_literals
from zope import interface, schema
#pylint: disable=E0213,E0211

_writer_base = interface.Interface
_reader_base = interface.Interface
_socket_base = None

try:
	import socketio.interfaces
	_writer_base = socketio.interfaces.ISocketIOWriter
	_reader_base = socketio.interfaces.ISocketIOReader
	_socket_base = socketio.interfaces.ISocketIOSocket
except ImportError:
	pass

class ISocketIOWriter(_writer_base):
	"""
	Defines the write-side of a socket (the ability to send messages to a client)
	"""

	externalize_function = schema.Field(
		description="The function used to externalize data to send to the client. Defaults to creating strings of JSON.",
		readonly=True)

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

	def send( message, destination=None ):
		"""
		Sends arbitrary message data to the connected client, or another client.

		:param message: The string of data to send
		:param destination: If given, the session id that should receive the data. Defaults
			to send the data to the connected client of this socket.
		"""

	def send_event( name, *args ):
		"""
		Sends a named event with structured arguments to the connected client.

		:param string name: The name of the event to send.
		:param args: The arguments the client's event handler should get, in order.
			Will be externalized to strings.
		"""

class ISocketIOReader(_reader_base):
	"""
	The read-side of a socket to a connected client.
	"""

if _socket_base:
	class ISocketIOSocket(ISocketIOReader,ISocketIOWriter,_socket_base):
		"""
		A socket to a connected client that can be used to read and write messages.
		"""
else:
	class ISocketIOSocket(ISocketIOReader,ISocketIOWriter,):
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
