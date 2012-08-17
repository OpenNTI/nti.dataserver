#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Connection and communication with the APNS.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent
from gevent import socket
from gevent import ssl

import time
import anyjson as json
import os
import struct
from pkg_resources import resource_filename

from zope import interface
from zope.event import notify
from . import interfaces as apns_interfaces


SERVER_PROD = 'gateway.push.apple.com'
SERVER_SAND = 'gateway.sandbox.push.apple.com'
PORT_PROD = 2195
PORT_SAND = 2195

DEFAULT_LIFETIME = 30 * 60 * 60

FEEDBACK_PROD = 'feedback.push.apple.com'
FEEDBACK_SAND = 'feedback.sandbox.push.apple.com'

FPORT_SAND = 2196
FPORT_PROD = 2196

MAX_PAYLOAD_SIZE = 256 # bytes

def to_payload_dictionary_string(payload):
	"""
	Convert a payload to the JSON dictionary string.

	:param payload: The payload object.
	:type payload: :class:`nti.apns.interfaces.INotificationPayload`
	"""

	aps = {k : getattr(payload, k)
		   for k in ('alert','sound','badge')
		   if getattr(payload, k, None) is not None}

	topLevel = {'aps': aps}
	if payload.userInfo:
		topLevel['nti'] = payload.userInfo
	result = json.dumps( topLevel )
	if len(result) > MAX_PAYLOAD_SIZE:
		# Hmm.
		logger.warning( 'Payload data too big, stripping extra' )
		if 'nti' in topLevel:
			del topLevel['nti']
			result = json.dumps( topLevel )

	# Make sure it's ASCII bytes
	if not isinstance( result, str ):
		result = result.encode( 'ascii' )

	if len(result) > MAX_PAYLOAD_SIZE:
		raise ValueError( "Payload too big" )
	return result

def to_packet_bytes(payload, deviceId):
	"""
	Transform the `payload` object into a sequence of bytes
	to send to the APNS server in `enhanced binary format`_

	:param payload: The payload object.
	:type payload: :class:`nti.apns.interfaces.INotificationPayload`

	.. _enhanced binary format: http://developer.apple.com/library/ios/#DOCUMENTATION/NetworkingInternet/Conceptual/RemoteNotificationsPG/CommunicatingWIthAPS/CommunicatingWIthAPS.html#//apple_ref/doc/uid/TP40008194-CH101-SW4
	"""
	# Create a packet in the 'enhanced' format
	command = 1
	identifier = id(payload) % 4294967295 # fit into 4 bytes
	expiry = time.time() + DEFAULT_LIFETIME
	deviceIdLength = len(deviceId) # should be 32
	assert deviceIdLength == 32

	payloadBytes = to_payload_dictionary_string( payload )

	# 1 byte command, 4 byte id, 4 byte expiry, 2 byte len, 4 byte devid, 2 byte len, payload
	packet = struct.pack( b'!bIih32sh',
						  command, identifier, expiry,
						  deviceIdLength, deviceId,
						  len(payloadBytes) )
	packet += payloadBytes

	return packet, identifier

def _close( connection ):
	try:
		connection.close()
	except Exception:
		pass

from repoze.lru import LRUCache

@interface.implementer( apns_interfaces.INotificationService )
class APNS(object):
	"""
	Encapsulates a connection to APNS for sending push notifications.
	Manages the connection lifetime.

	Based on GEvent for non-blocking, cooperative socket access.
	"""

	_feedback_greenlet = None
	_apns_error_greenlet = None

	def __init__( self, host=SERVER_SAND, port=PORT_SAND, certFile=None,
				  feedbackHost=FEEDBACK_SAND, feedbackPort=FPORT_SAND ):
		if host == SERVER_SAND and port == PORT_SAND and 'APNS_PROD' in os.environ:
			host = SERVER_PROD
			port = PORT_PROD
		self.feedbackHost = feedbackHost
		self.feedbackPort = feedbackPort
		self.host = host
		self.port = port
		self.certFile = certFile
		if self.certFile is None:
			localCert = 'NextThoughtPOCCertDev.pem'
			if 'APNS_PROD' in os.environ:
				localCert = 'NextThoughtPOCCertProd.pem'
			self.certFile = resource_filename(__name__, localCert )
		self.connection = None
		self.selecting = None
		self.blacklisted_devices = set()
		self.recent_notifications = LRUCache( 100 )



	def _read_apns_errors(self, connection):
		def read_apns_errors():
			cmd, status, ident = None, None, None
			# Block and read (in a greenlet). The first
			# time we get any data should be immediately
			# before we are forcibly disconnected anyway,
			# so no need to loop
			try:
				response = connection.recv( 8 )
				if response:
					cmd, status, ident = struct.unpack( b'!bBI', response )
					logger.info( "Disconnected from APNS because we sent bad data: %s %s %s",
								 cmd, status, ident )
					if status == 8: # Invalid token. So this will keep happening until we remove the token. (Apple docs, table 5-1)
						if self.recent_notifications.get( ident ):
							deviceId, payload = self.recent_notifications.get( ident )
							self.blacklisted_devices.add( deviceId )
							# Then try to clean it up
							try:
								fb = apns_interfaces.APNSDeviceFeedback(0, deviceId)
								notify( fb )
							except Exception:
								logger.exception( "Failed to remove invalid device id %s sending %s", deviceId.encode( 'hex'), payload )
			except (IOError, struct.error):
				logger.debug( "Error stream from APNS disconnected", exc_info=True )
			except Exception:
				logger.exception( "Unexpected exception reading from APNS." )
			finally:
				_close( connection )
				if self.connection is connection:
					self._apns_error_greenlet = None
					self.connection = None

		self._apns_error_greenlet = gevent.spawn( read_apns_errors )

	def _read_feedback( self ):
		"""
		Spawns a greenlet and connects to the feedback
		server, reading all invalid devices and broadcasting that
		information.
		"""

		sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
		connection = ssl.wrap_socket( sock, certfile=self.certFile )
		connection.connect( (self.feedbackHost,self.feedbackPort) )

		def read_feedback( ):
			try:
				while True:
					try:
						buf = connection.recv(38)
						if buf:
							unpacked = struct.unpack( '!lh32s' )
							fb = apns_interfaces.APNSDeviceFeedback( unpacked(0), unpacked(2) )
							notify( fb )
						else:
							logger.debug( "No data to read from feedback service" )
							break
					except (IOError,struct.error):
						logger.exception( "Failed to read feedback." )
						break
			finally:
				_close( connection )
				self._feedback_greenlet = None


		self._feedback_greenlet = gevent.spawn( read_feedback )


	def _makeConnection(self):
		""" Creates or returns a connection. """
		if self.connection is None:
			try:
				sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
				connection = ssl.wrap_socket( sock, certfile=self.certFile )
				connection.connect( (self.host,self.port) )

				self._read_apns_errors( connection )
				self.connection = connection
				if self._feedback_greenlet is None:
					self._read_feedback()
			except (IOError,TypeError):
				# TypeError: must be _socket.socket, not closedsocket
				logger.exception( "Failed to connect to APNS" )
				self.connection = None
		return self.connection

	def sendNotification( self, deviceId, payload ):
		""" Directs a notification with the ``payload`` to the given
		``deviceId``. The notification may be sent now or it
		may be batched up and sent later. ``payload`` is an :class:`APNSPayload` object."""

		if deviceId in self.blacklisted_devices:
			logger.debug( "Refusing to talk to blacklisted device %s", deviceId.encode('hex') )
			return

		# For now, we send immediately
		connection = self._makeConnection()
		if not connection:
			return

		packet, ident = to_packet_bytes( payload, deviceId )
		self.recent_notifications.put( ident, (deviceId, payload) )

		try:
			connection.sendall( packet )
		except IOError:
			logger.warning( "Failed to send data", exc_info=True )
			# If we actually close this connection now, then we probably won't
			# be able to read our response code, which we need to get the bad device
			#_close( connection ) # Which will trigger the reading greenlet to die quietly
			if self.connection is connection:
				self.connection = None

		return packet


	def close( self ):
		_close( self.connection )
		self.connection = None
		if self._feedback_greenlet is not None:
			self._feedback_greenlet.kill(block=False)
