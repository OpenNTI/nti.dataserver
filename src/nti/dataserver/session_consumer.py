#!/usr/bin/env python2.7
""" Handles a socket.io session. """

import logging
logger = logging.getLogger( __name__ )

import sys
import itertools

from nti.dataserver.datastructures import toExternalObject

from nti.socketio import interfaces as sio_interfaces
import nti.externalization.internalization

from persistent import Persistent

from zope import component

class UnauthenticatedSessionError(ValueError):
	"Raised when a session consumer is called but is not authenticated."

class SessionConsumer(Persistent):
	"""
	A callable object that responds to events from a client session.

	Maintains the authentication state of the client, and the dispatch map for
	event handling.
	"""

	def __init__(self, username=None, session=None):
		self._username = username
		self._event_handlers = {}
		if session and username:
			logger.info( "Initializing authenticated session for '%s'", self._username )
			self._initialize_session(session)


	def __call__( self, socket_obj, msg ):
		if self._username is None:
			raise UnauthenticatedSessionError()

		self._on_msg( socket_obj, msg )

	def _initialize_session(self, session):
		session.owner = self._username # save the username, cannot save user obj
		session.incr_hits()

		self._event_handlers.update( self._create_event_handlers( session.protocol_handler, session ) )

		#if session.internalize_function == plistlib.readPlistFromString:
		#	session.externalize_function = to_external_representation

	def _create_event_handlers( self, socket_obj, session=None ):
		"""
		:return: A mapping from event prefix (empty string for no prefix) no list of possible
			handlers for that prefix.
		"""
		subscribers = component.subscribers( (socket_obj,), sio_interfaces.ISocketEventHandler )
		if session is not None:
			subscribers = itertools.chain( subscribers,
										   component.subscribers( (session,), sio_interfaces.ISocketEventHandler ) )
		result = dict()
		for subscriber in subscribers:
			if subscriber is None: continue
			pfx = getattr( subscriber, 'event_prefix', '' )
			result.setdefault( pfx, [] ).append( subscriber )

		return result

	def kill( self ):
		"""
		Call while a session is being killed to teardown chat connections.
		Any event handler with a 'destroy' method will be invoked.
		"""
		for v in itertools.chain( *self._event_handlers.values() ):
			destroy = getattr( v, 'destroy', None )
			if callable(destroy): destroy()


	def _find_handler( self, message ):
		"""
		:return: A callable object of zero arguments, or None.
		"""
		event = message['name']
		namespace = event
		if '_' in event:
			namespace = event[0:event.index('_')]
			event = event[event.index('_') + 1:]

		def l(): logger.warning( "Dropping unhandled event '%s' from message %s", event, message )

		handler_list = self._event_handlers.get(namespace)
		if not handler_list:
			l()
			return

		if event != namespace:
			handler_list = [getattr( handler, event, None ) for handler in handler_list]
			handler_list = [handler for handler in handler_list if handler]

		if not handler_list:
			l()
			return

		def call():
			"""
			Call the handlers in order, passing the arguments. The last non-None
			result from a handler will be our result.
			"""
			last_result = None
			for h in handler_list:
				# TODO Exception handling? We're simply propagating the first one and
				# failing to call any subsequent handlers. This is probably OK if everything
				# is transactional...
				# Note that we're converting the input to objects for each
				# handler in the list. This could be a little inefficient in the case
				# of multiple handlers that come from related packages.
				args = _convert_message_args_to_objects( h, message )
				#logger.debug( "Handling message using %s(%s)", h, args )
				result = h(*args)
				if result is not None:
					last_result = result
			return last_result

		return call

	def _on_msg( self, socket_obj, message ):
		if message is None:
			# socket has died
			logger.debug( "Socket has died %s", socket_obj )
			return
		if message['type'] != 'event':
			logger.warning( 'Dropping unhandled message of wrong type %s', message )
			return

		handler = self._find_handler( message ) # This logs missing handlers
		if handler is None:
			return


		try:
			result = handler( )
			if message.get('id'):
				# they expect a response. Note that ack
				# is unlike 'send_event' and requires that the args be
				# pre-packed as an array. (This is due to how the JS expects
				# to find packet.args as an array)
				result = [toExternalObject(result)]
				socket_obj.ack( message['id'], result )
		except component.ComponentLookupError:
				# This is a programming error we can and should fix
				raise
		except Exception as e:
			# TODO: We should have a system of error codes in place
			logger.exception( "Exception handling event %s", message )
			socket_obj.send_event( 'server-error', str(e) )


def _convert_message_args_to_objects( handler, message ):
	"""
	Convert the list/dictionary external (incoming) structures into objects to pass to
	the handler.

	:param handler: The handler we will call. Used to inform the conversion process.
		The module of the handler (or its class) will be searched for registered
		types. If the handler (or its class) declares a `_session_consumer_args_search_`
		attribute that is an iterable of module names, those modules will be searched as well.
	:return: A list of argument objects
	"""
	args = []
	# We use the dataserver to handle the conversion. We
	# inspect the handler to find out where it lives so that we can
	# limit the types the dataserver needs to search.
	search_modules = ['nti.dataserver.users', 'nti.dataserver.contenttypes']
	def handlers_from_class( cls ):
		mods = getattr( cls, '_session_consumer_args_search_', () )
		search_modules.extend( mods )
	if hasattr( handler, 'im_class' ):
		#bound method
		search_modules.append( sys.modules[handler.im_class.__module__] )
		handlers_from_class( handler.im_class )
	elif isinstance( handler, type ):
		#callable class
		search_modules.append( sys.modules[handler.__module__] )
		handlers_from_class( handler )
	else:
		handlers_from_class( handler )

	for mod in search_modules:
		nti.externalization.internalization.register_legacy_search_module( mod )

	for arg in message['args']:
		extType = nti.externalization.internalization.find_factory_for( arg )

		if extType:
			arg = nti.externalization.internalization.update_from_external_object( extType(), arg )
		args.append( arg ) # strings and such fall through here

	return args
