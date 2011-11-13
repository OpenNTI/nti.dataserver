import logging
logger = logging.getLogger( __name__ )

import struct
import socket
import traceback

class AbstractWebSocket(object):
	def __init__(self, sock, rfile, environ):
		self.rfile = rfile
		self.socket = sock
		self.origin = environ.get('HTTP_ORIGIN')
		self.protocol = environ.get('HTTP_SEC_WEBSOCKET_PROTOCOL', 'unknown')
		self.path = environ.get('PATH_INFO')
		self.websocket_closed = False

	def send(self, message):
		raise NotImplementedError()

	def close_connection(self):
		if not self.websocket_closed:
			self.websocket_closed = True
			try:
				self.socket.shutdown(socket.SHUT_RDWR)
				self.socket.close()
			except:
				logging.debug("When closing web socket.", exc_info=True)
		else:
			return

	def _message_length(self):
		# TODO: buildin security agains lengths greater than 2**31 or 2**32
		length = 0

		while True:
			byte_str = self.rfile.read(1)

			if not byte_str:
				return 0
			else:
				byte = ord(byte_str)

			if byte != 0x00:
				length = length * 128 + (byte & 0x7f)
				if (byte & 0x80) != 0x80:
					break

		return length

	def _read_until(self):
		bytes = []

		while True:
			byte = self.rfile.read(1)
			if ord(byte) != 0xff:
				bytes.append(byte)
			else:
				break

		return ''.join(bytes)

	def wait(self):
		while True:
			if self.websocket_closed:
				return None

			frame_str = self.rfile.read(1)
			if not frame_str:
				# Connection lost?
				self.close_connection()
				continue
			else:
				frame_type = ord(frame_str)


			if (frame_type & 0x80) == 0x00: # most significant byte is not set

				if frame_type == 0x00:
					bytes = self._read_until()
					return bytes.decode("utf-8", "replace")
				else:
					self.close_connection()

			elif (frame_type & 0x80) == 0x80: # most significant byte is set
				# Read binary data (forward-compatibility)
				if frame_type != 0xff:
					self.close_connection()
				else:
					length = self._message_length()
					if length == 0:
						self.close_connection()
					else:
						self.rfile.read(length) # discard the bytes
			else:
				raise IOError("Reveiced an invalid message")


class WebSocket76(AbstractWebSocket):


	def send(self, message):
		#print self, 'sending', message
		if self.websocket_closed:
			raise Exception("Connection was terminated")

		if isinstance(message, unicode):
			message = message.encode('utf-8')
		elif isinstance(message, str):
			message = unicode(message).encode('utf-8')
		else:
			raise Exception("Invalid message encoding")

		self.socket.sendall("\x00" + message + "\xFF")


	def _message_length(self):
		# TODO: buildin security agains lengths greater than 2**31 or 2**32
		length = 0

		while True:
			byte_str = self.rfile.read(1)

			if not byte_str:
				return 0
			else:
				byte = ord(byte_str)

			if byte != 0x00:
				length = length * 128 + (byte & 0x7f)
				if (byte & 0x80) != 0x80:
					break

		return length

	def _read_until(self):
		bytes = []

		while True:
			byte = self.rfile.read(1)
			if ord(byte) != 0xff:
				bytes.append(byte)
			else:
				break

		return ''.join(bytes)

	def wait(self):
		while True:
			if self.websocket_closed:
				return None

			frame_str = self.rfile.read(1)
			if not frame_str:
				# Connection lost?
				self.close_connection()
				continue
			else:
				frame_type = ord(frame_str)


			if (frame_type & 0x80) == 0x00: # most significant byte is not set

				if frame_type == 0x00:
					bytes = self._read_until()
					return bytes.decode("utf-8", "replace")
				else:
					self.close_connection()

			elif (frame_type & 0x80) == 0x80: # most significant byte is set
				# Read binary data (forward-compatibility)
				if frame_type != 0xff:
					self.close_connection()
				else:
					length = self._message_length()
					if length == 0:
						self.close_connection()
					else:
						self.rfile.read(length) # discard the bytes
			else:
				raise IOError("Reveiced an invalid message")


class WebSocket7(AbstractWebSocket):

	def send( self, message ):
		#print self, 'sending text message', message
		# We only send text messages.
		message = message.encode( 'utf-8' )

		flag_and_opcode = 0x81 # 1000 0001
		mask_and_len = None
		if len(message) < 126:
			mask_and_len = (len(message),)
		elif len(message) < 0xFFFF:
			# Three bytes
			mask_and_len = [ 126, (len(message) & 0xFF00) >> 8, len(message) & 0xFF ]
		else:
			raise NotImplementedError( 'Implement 64-bit lengths' )
		masking_key = ()

		self.socket.send( struct.pack( 'B', flag_and_opcode ) )
		for i in mask_and_len:
			#print 'mask and len', i
			self.socket.send( struct.pack( 'B', i ) )
		for i in masking_key: self.socket.send( struct.pack( 'B', i ) )

		self.socket.sendall( message )

	def wait(self):
		while not self.websocket_closed:
			frame_str = self.rfile.read(1)
			if not frame_str:
				# Connection lost?
				# print 'failed to read from socket'
				self.close_connection()
				break
			frame_str = ord(frame_str)
			# Ignore the top bits. We assume
			# there's no fragmentation.
			if frame_str & 0x80 == 0:
				raise IOError( "Unable to deal with fragmentation" )

			opcode = frame_str & 0x0F
			if opcode == 1:
				# print 'Reading text'
				return self._read_client_data().decode( 'utf-8' )
			if opcode == 2:
				return self._read_client_data()
			if opcode == 8:
				# aww, close connection
				self.close_connection()
				break

			if opcode == 9:
				# Got a ping, must send a pong
				raise NotImplementedError( "Must pong" )

			raise IOError( "Received unknown opcode" )

		#print 'returning None because closed'
		return None

	def _read_client_data( self ):
		"""
		Call after reading the first byte of a frame.
		"""
		mask_and_len = ord(self.rfile.read( 1 ))
		if mask_and_len & 0x80 != 0x80:
			raise IOError( "Client sent unmasked data." )
		client_len = mask_and_len & 0x7F
		if client_len == 126:
			b1 = ord(self.rfile.read( 1 )) << 8
			b2 = ord(self.rfile.read( 1 ))
			client_len = b1 | b2
		elif client_len == 127:
			raise NotImplementedError( "Implement 64-bit lengths" )
		mask = []
		for i in xrange( 4 ):
			mask.append( ord(self.rfile.read( 1 )) )

		cntr = 0
		bytes = []
		for i in xrange( client_len ):
			the_byte = ord(self.rfile.read( 1 ))
			bytes.append( chr(the_byte ^ mask[i % 4]) )
		return ''.join( bytes )

WebSocket8 = WebSocket7
WebSocket13 = WebSocket7
