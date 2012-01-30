"""Support for the Apple Push Notification Service."""

import logging
logger = logging.getLogger( __name__ )

import socket
import ssl
import time
import json
import os
import struct
from pkg_resources import resource_filename

from zope import interface
from zope.event import notify
from . import interfaces as apns_interfaces

from zmq.eventloop import IOLoop


SERVER_PROD = 'gateway.push.apple.com'
SERVER_SAND = 'gateway.sandbox.push.apple.com'
PORT_PROD = 2195
PORT_SAND = 2195

DEFAULT_LIFETIME = 30 * 60 * 60

FEEDBACK_PROD = 'feedback.push.apple.com'
FEEDBACK_SAND = 'feedback.sandbox.push.apple.com'

FPORT_SAND = 2196
FPORT_PROD = 2196

class APNSDeviceFeedback(object):
	""" Represents feedback about a device from APNS. """

	interface.implements( apns_interfaces.IDeviceFeedbackEvent )

	def __init__( self, timestamp, deviceId ):
		super(APNSDeviceFeedback,self).__init__()
		self.timestamp = timestamp
		self.deviceId = deviceId

	def __repr__( self ):
		return "APNSDeviceFeedback(%s,%s)" % (self.timestamp, self.deviceId.encode('hex'))

class APNSPayload(object):
	""" Represents the payload of a APNs remote notification. """

	interface.implements( apns_interfaces.INotificationPayload )

	DEFAULT_SOUND = 'default'
	MAX_PAYLOAD_SIZE = 256

	def __init__(self, alert=None, badge=None, sound=None, userInfo=None ):
		""" `alert' is a string, `badge' is a number or none, `sound' is a string.
		If userInfo is given, it must be a (small) dictionary that can work with json;
		it will be placed as a top-level key called 'nti'"""
		super( APNSPayload, self ).__init__()
		self.alert = alert
		self.badge = badge
		self.sound = sound
		self.nti = userInfo

	def toPacketFormat(self):
		aps = {k : getattr(self, k) for k in ('alert','sound','badge')
				  if getattr(self, k, None) is not None}
		topLevel = {'aps': aps}
		if self.nti:
			topLevel['nti'] = self.nti
		result = json.dumps( topLevel )
		if len(result) > self.MAX_PAYLOAD_SIZE:
			# Hmm.
			logger.warning( 'Payload data too big, stripping extra' )
			if self.nti:
				del topLevel['nti']
				result = json.dumps( topLevel )
		return result


class APNS(object):
	""" Encapsulates a connection to APNS for sending
	push notifications. Manages the connection lifetime. Depends on
	someone pumping the ZMQ eventloop. """

	interface.implements( apns_interfaces.INotificationService )

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

	def _readFeedback( self ):
		""" Spawns a thread and connects to the feedback
		server, reading all invalid devices and broadcasting that
		information. """

		sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
		connection = ssl.wrap_socket( sock, certfile=self.certFile )
		connection.connect( (self.feedbackHost,self.feedbackPort) )
		def on_event( fd, events ):
			if events & IOLoop.ERROR:
				# We're done.
				try:
					IOLoop.instance().remove_handler( fd )
				except: pass
				try:
					connection.shutdown(socket.SHUT_RDWR)
				except socket.error: pass
				try:
					connection.close()
				except socket.error: pass
			elif events & IOLoop.READ:
				try:
					buf = connection.recv(38)
					if buf:
						unpacked = struct.unpack( '!lh32s' )
						fb = APNSDeviceFeedback( unpacked(0), unpacked(2) )
						notify( fb )
				except Exception:
					logger.exception( "Failed to read feedback." )

		IOLoop.instance().add_handler( connection.fileno(), on_event, IOLoop.READ | IOLoop.ERROR )

	def _watch( self, connection ):
		""" Looks for the connection to become invalid
		or have something written by APNs"""

		apns = self
		def on_event( fd, events ):
			# anytime we get here it was due to error
			# so stop polling
			IOLoop.instance().remove_handler( fd )
			apns.connection = None
			apns.selecting = None
			if events & IOLoop.ERROR:
				pass
			else: # must be read
				connection.setblocking( True )
				response = connection.recv(  )
				try:
					print 'Response: ', response
					cmd, status, ident = struct.unpack( '!bBI', response )
					print 'Command', cmd, 'Status', status, 'ident', ident
				finally:
					apns.connection = None

		if self.selecting:
			# in case of reusing file descriptor numbers,
			# must do this before we add a new handler
			try:
				IOLoop.instance().remove_handler( self.selecting )
			except KeyError: pass
			self.selecting = None

		# ZMQ IOLoop has a bug, must pass the fileno itself not the object,
		# it fails to reverse map from fileno to object when getting the handler
		IOLoop.instance().add_handler( connection.fileno(), on_event, IOLoop.READ | IOLoop.ERROR )
		self.selecting = connection.fileno()


	def _makeConnection(self):
		""" Creates or returns a connection. """
		if self.connection is None:
			try:
				sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
				self.connection = ssl.wrap_socket( sock, certfile=self.certFile )
				self.connection.connect( (self.host,self.port) )
				print self.host, self.port, self.certFile
				self._watch( self.connection )
				self._readFeedback()
			except IOError:
				logger.exception( "Failed to connect to APNS" )
		return self.connection

	def sendNotification( self, deviceId, payload ):
		""" Directs a notification with the `payload' to the given
		`deviceId'. The notification may be sent now or it
		may be batched up and sent later. `payload' is an APNSPayload object."""

		# For now, we send immediately
		connection = self._makeConnection()
		if not connection: return

		# Create a packet in the 'enhanced' format
		command = 1
		identifier = id(payload) % 4294967295 # fit into 4 bytes
		expiry = time.time() + DEFAULT_LIFETIME
		deviceIdLength = len(deviceId) # should be 32
		payloadBytes = payload.toPacketFormat()
		# 1 byte command, 4 byte id, 4 byte expiry, 2 byte len, 4 byte devid, 2 byte len, payload
		packet = struct.pack( '!bIih32sh',
					 command, identifier, expiry,
					 deviceIdLength, deviceId,
					 len(payloadBytes) )
		packet += payloadBytes

		try:
			connection.sendall( packet )
		except IOError:
			logger.warning( "Failed to send data", exc_info=True )
			self.reset( connection )


		return packet

	def reset(self, c=None):
		connection = c or self.connection
		try:
			connection.shutdown( socket.SHUT_RDWR )
		except IOError: pass
		finally:
			try:
				connection.close()
			except IOError: pass
		if self.selecting:
			try:
				IOLoop.instance().remove_handler( self.selecting )
			except KeyError: pass
			self.selecting = None
		self.connection = None

	def close( self ):
		self.reset()

