""" Manages state and state transitions for a session. """

import logging
logger = logging.getLogger( __name__ )

import _Dataserver as dataserver
from datastructures import to_external_representation
from users import User
import sys
import plistlib

from persistent import Persistent

class SessionConsumer(Persistent):

	def __init__(self):
		self.username = None
		self.event_handlers = {}

	def __call__( self, socket_obj, msg ):
		# The first time they speak to us, we
		# can infer the client format, be it JSON or
		# PList.
		if self.username is None:
			self._auth_user( socket_obj, msg )
		else:
			self._on_msg( socket_obj, msg )

	def _auth_user( self, socket_obj, msg ):
		# As mentioned before, we have no authentication support
		# so we have to roll our own somehow. We default
		# to just using authentication like the browser does, asking
		# for that to be the first thing in the stream.
		pw = None
		try:
			self.username, pw = msg['args']
		except:
			# Notice that we're grapping a new protocol object.
			# The one captured by the greenlet will not be the one
			# that actually just read that bad data---so when
			# we try to send to the client, if we didn't do this,
			# we could use the wrong format.
			# This would be fixed by making the protocol object delegate
			# to the session (all state should live in the session object)
			socket_obj = socket_obj.session.new_protocol( socket_obj.handler )
			socket_obj.send_event( 'serverkill', 'Invalid auth' )
			socket_obj.send( "0" ) # socket.io disconnect
			return

		with dataserver.Dataserver.get_shared_dataserver().dbTrans():
			ent = User.get_user( self.username )
			# TODO: Centralize this.
			if not ent or not ent.password == pw:
				socket_obj = socket_obj.session.new_protocol( socket_obj.handler )
				socket_obj.send_event( 'serverkill', 'Invalid auth' )
				socket_obj.send( "0" )
				return

		socket_obj.session.owner = self.username # save the username, cannot save user obj
		socket_obj.session.incr_hits()

		self.event_handlers = {'chat': dataserver.Dataserver.get_shared_dataserver().chatserver.handlerFor( socket_obj )}

		if socket_obj.session.internalize_function == plistlib.readPlistFromString:
			socket_obj.session.externalize_function = to_external_representation

	def kill( self ):
		"""
		Call while a session is being killed to teardown chat connections.
		"""
		chat_handler = self.event_handlers.get( 'chat' )
		if chat_handler:
			chat_handler.destroy()

	def _on_msg( self, socket_obj, message ):
		if message is None:
			# socket has died
			return
		if message['type'] == 'event':
			event = message['name']
			namespace = event
			if '_' in event:
				namespace = event[0:event.index('_')]
				event = event[event.index('_') + 1:]

			handler = self.event_handlers.get(namespace)
			if event != namespace:
				handler = getattr( handler, event, None )
			if handler:
				args = []
				search_modules = [dataserver.users, dataserver.contenttypes]
				if hasattr( handler, 'im_class' ):
					#bound method
					search_modules.append( sys.modules[handler.im_class.__module__] )
				elif isinstance( handler, type ):
					#callable class
					search_modules.append( sys.modules[handler.__module__] )
				ds = dataserver.Dataserver.get_shared_dataserver()
				for arg in message['args']:
					extType = ds.get_external_type( arg,
													searchModules=search_modules )
					if extType:
						arg = ds.update_from_external_object( extType(), arg )
					args.append( arg )
				try:
					handler( *args )
				except Exception:
					# TODO: Think about exceptions and return types.
					# There should be a protocol to pass values to the client:
					# maybe if the return is a dictionary it is an event?
					# What about passing exceptions?
					logger.exception( "Exception handling event %s", message )
			else:
				logger.warning( 'Dropping unhandled event %s from message %s', event, message )
		else:
			logger.warning( 'Dropping unhandled message %s', message )
