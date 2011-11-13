import gevent
import anyjson as json
import plistlib

class SocketIOProtocol(object):
	"""SocketIO protocol specific functions."""

	def __init__(self, handler):
		self.handler = handler
		self.session = None

	@property
	def externalize_function(self):
		return self.session.externalize_function

	def _get_internalize_function(self):
		return self.session.internalize_function

	def _set_internalize_function( self, f ):
		self.session.internalize_function = f

	internalize_function = property( _get_internalize_function, _set_internalize_function )

	def ack(self, msg_id, params):
		self.send("6:::%s%s" % (msg_id, self.externalize_function(params)))

	def send(self, message, destination=None):
		if destination is None:
			dst_client = self.session
		else:
			dst_client = self.handler.server.sessions.get(destination)

		self._write(message, dst_client)

	def send_event(self, name, *args):
		self.send("5:::" + self.externalize_function({'name': name, 'args': args}))

	def receive(self):
		"""Wait for incoming messages."""

		return self.session.get_server_msg()

	def broadcast(self, message, exceptions=None, include_self=False):
		"""
		Send messages to all connected clients, except itself and some
		others.
		FIXME: does not apply the correct transformations.
		"""
		if exceptions is None:
			exceptions = []

		if not include_self:
			exceptions.append(self.session.session_id)

		for session_id, session in self.handler.server.sessions.iteritems():
			if session_id not in exceptions:
				self._write(message, session)

	def broadcast_event(self, name, *args, **kwargs):
		self.broadcast("5:::" + json.dumps({'name': name, 'args': args}), **kwargs)

	def start_heartbeat(self):
		"""Start the heartbeat Greenlet to check connection health."""
		def ping():
			self.session.state = self.session.STATE_CONNECTED

			while self.session.connected:
				gevent.sleep(5.0) # FIXME: make this a setting
				self.send_heartbeat()

		return gevent.spawn(ping)

	def send_heartbeat( self ):
		self.send( "2::")

	def _write(self, message, session=None):
		if session is None:
			raise Exception("No client with that session exists")
		else:
			session.put_client_msg(message)

	def encode(self, message):
		if isinstance(message, basestring):
			encoded_msg = message
		elif isinstance(message, (object, dict)):
			return self.encode(self.externalize_function(message))
		else:
			raise ValueError("Can't encode message")

		return encoded_msg

	def _parse_data( self, data ):
		data = data.lstrip()
		# We make some assumptions here in the interests
		# of optimization. The alternate approach is to
		# catch an exception thrown by internalize_function
		# and then do content sniffing
		result = data
		if data.startswith( '<' ):
			# XML format. Never valid in JSON
			result = plistlib.readPlistFromString( str(data) )
			# Things that will send us XML will only ever want
			# to get XML. Go ahead and note that now.
			if self.session:
				self.internalize_function = plistlib.readPlistFromString
		else:
			result = self.internalize_function( data )
		return result

	def decode(self, data):
		msg_type, msg_id, tail = data.split(":", 2)

		# 'disconnect'
		# 'connect'
		# 'heartbeat'
		# 'message'
		# 'json'
		# 'event'
		# 'ack'
		# 'error'
		# 'noop'


		if msg_type == "0": # disconnect
			self.session.kill()
			return None

		if msg_type == "1": # connect
			self.send("1::%s" % tail)
			return None

		if msg_type == "2": # heartbeat
			self.session.heartbeat()
			return None
		message = None
		msg_endpoint, data = tail.split(":", 1)
		data = data.decode( 'utf-8', 'replace' )
		if msg_type == "3": # message
			message = {
				'type': 'message',
				'data': data,
			}
		elif msg_type == "4": # json
			message = self._parse_data(data)
		elif msg_type == "5": # event
			message = self._parse_data(data)

			if "+" in msg_id:
				message['id'] = msg_id
			else:
				pass # TODO send auto ack
			message['type'] = 'event'
		else:
			raise Exception("Unknown message type: %s" % msg_type)

		return message

	def decode_multi( self, data ):
		DELIM1 = '\xff\xfd' #u'\ufffd'
		DELIM2 = '\xef\xbf\xbd' # utf-8 encoding

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
			assert len_str > 0
			end_data = end + dl + len_str
			sub_data = data[end+dl:end_data]
			assert sub_data, "Data from %s to %s was not len %s (got %s)" % (start_search, end_data, len_str, sub_data )
			assert len(sub_data) == len_str, "Data from %s to %s was not len %s (got %s)" % (start_search, end_data, len_str, sub_data )
			messages.append( self.decode( sub_data ) )

			start = end_data

		return messages
