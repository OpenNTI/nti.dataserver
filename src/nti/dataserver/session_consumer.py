#!/usr/bin/env python2.7
""" Handles a socket.io session. """

import logging
logger = logging.getLogger( __name__ )

import sys
import plistlib
import warnings
import itertools

from nti.dataserver.datastructures import to_external_representation
from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
import nti.dataserver.users
import nti.dataserver.contenttypes

from persistent import Persistent

from zope import component

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
		# The first time they speak to us, we
		# can infer the client format, be it JSON or
		# PList.
		if self._username is None:
			self._auth_user( socket_obj, msg )
		else:
			self._on_msg( socket_obj, msg )

	def _initialize_session(self, session):
		session.owner = self._username # save the username, cannot save user obj
		session.incr_hits()

		self._event_handlers.update( self._create_event_handlers( session.protocol_handler ) )

		if session.internalize_function == plistlib.readPlistFromString:
			session.externalize_function = to_external_representation

	def _create_event_handlers( self, socket_obj ):
		"""
		:return: A mapping from event prefix (empty string for no prefix) no list of possible
			handlers for that prefix.
		"""
		subscribers = component.subscribers( (socket_obj,), nti_interfaces.ISocketEventHandler )
		result = dict()
		for subscriber in subscribers:
			if subscriber is None: continue
			pfx = getattr( subscriber, 'event_prefix', '' )
			result.setdefault( pfx, [] ).append( subscriber )

		return result

	def _auth_user( self, socket_obj, msg ):
		# As mentioned before, we have no authentication support
		# so we have to roll our own somehow. We default
		# to just using authentication like the browser does, asking
		# for that to be the first thing in the stream.
		pw = None
		uname = None
		def invalid_auth(msg=None):
			if msg:
				logger.debug( msg )
			# Notice that we're grabbing a new protocol object.
			# The one captured by the greenlet will not be the one
			# that actually just read that bad data---so when
			# we try to send to the client, if we didn't do this,
			# we could use the wrong format.
			# This would be fixed by making the protocol object delegate
			# to the session (all state should live in the session object)
			p = socket_obj.session.new_protocol( socket_obj.handler )
			p.send_event( 'serverkill', 'Invalid auth' )
			p.send( "0" ) # socket.io disconnect

		try:
			uname, pw = msg['args']
		except (KeyError,ValueError):
			invalid_auth( "Failed socket auth: wrong arguments" )
			return

		with component.getUtility( nti_interfaces.IDataserver ).dbTrans():
			ent = User.get_user( uname )
			# TODO: Centralize this.
			warnings.warn( "Code is assuming authentication protocol." )
			if not ent or not ent.password == pw:
				invalid_auth( "Failed socket auth: wrong password or user" )
				return

		self._username = uname
		self._initialize_session( socket_obj.session )


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
				# they expect a response
				try:
					socket_obj.ack( message['id'], result )
				except TypeError:
					if result is not None: raise
					# plistlib cannot serializae None, try false
					socket_obj.ack( message['id'], False )
		except Exception as e:
			# TODO: We should have a system of error codes in place
			logger.exception( "Exception handling event %s", message )
			socket_obj.send_event( 'server-error', str(e) )


def _convert_message_args_to_objects( handler, message ):
	"""
	Convert the list/dictionary external (incoming) structures into objects to pass to
	the handler.

	:param handler: The handler we will call. Used to inform the conversion process
	:return: A list of argument objects
	"""
	args = []
	# We use the dataserver to handle the conversion. We
	# inspect the handler to find out where it lives so that we can
	# limit the types the dataserver needs to search.
	search_modules = [nti.dataserver.users, nti.dataserver.contenttypes]
	if hasattr( handler, 'im_class' ):
		#bound method
		search_modules.append( sys.modules[handler.im_class.__module__] )
	elif isinstance( handler, type ):
		#callable class
		search_modules.append( sys.modules[handler.__module__] )

	ds = component.getUtility( nti_interfaces.IDataserver )
	for arg in message['args']:
		extType = ds.get_external_type( arg,
										searchModules=search_modules )
		if extType:
			arg = ds.update_from_external_object( extType(), arg )
		args.append( arg ) # strings and such fall through here

	return args
