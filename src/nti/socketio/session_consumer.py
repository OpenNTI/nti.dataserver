#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Handles a socket.io session.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import itertools
import simplejson as json
from collections import defaultdict

from zope import component
from zope import interface
from zope.interface.exceptions import Invalid

from zope.cachedescriptors.method import cachedIn

from zope.event import notify

from zope.i18n import translate

import transaction

from nti.externalization.persistence import NoPickle
from nti.externalization.externalization import toExternalObject

from .interfaces import ISocketEventHandler
from .interfaces import ISocketEventHandlerClientError
from .interfaces import ISocketSessionClientMessageConsumer

class UnauthenticatedSessionError(ValueError):
	"Raised when a session consumer is called but is not authenticated."

@interface.implementer(ISocketSessionClientMessageConsumer)
@NoPickle
class SessionConsumer(object):
	"""
	A callable object that responds to events from a client session.

	Maintains the authentication state of the client, and the dispatch map for
	event handling.
	"""

	def __call__( self, session, msg ):
		if session.owner is None:
			raise UnauthenticatedSessionError()

		event_handlers = self._initialize_session( session )
		return self._on_msg( event_handlers, session, msg )

	def _initialize_session(self, session):
		"""
		:return: The event handlers that are interested in the session.
		"""
		session.incr_hits()

		return self._create_event_handlers( session.socket, session )

	# we expect to be getting the same socket and session object
	# over and over because we are actually a cached property on the session
	# which in turn caches its socket, so it's effective to cache
	# the handlers
	@cachedIn('_v_create_event_handlers')
	def _create_event_handlers( self, socket_obj, session=None ):
		"""
		:return: A mapping from event prefix (empty string for no prefix) no list of possible
			handlers for that prefix.
		"""
		subscribers = component.subscribers( (socket_obj,), ISocketEventHandler )
		if session is not None:
			subscribers = itertools.chain( subscribers,
										   component.subscribers( (session,), ISocketEventHandler ) )
		result = defaultdict(list)
		for subscriber in subscribers:
			if subscriber is None:
				continue
			pfx = getattr( subscriber, 'event_prefix', '' )
			result[pfx].append( subscriber )

		return result

	def kill( self, session ):
		"""
		Call while a session is being killed to teardown chat connections.
		Any event handler with a 'destroy' method will be invoked.
		"""
		for v in itertools.chain( *self._create_event_handlers(session.socket,session).values() ):
			destroy = getattr( v, 'destroy', None )
			if callable(destroy):
				destroy()

	@cachedIn('_v_event_handlers_in_namespace')
	def __event_handlers_for_event_in_namespace(self, handler_list, event, namespace):
		"""
		For caching optimization. Handler_list must be a tuple.
		"""
		if not handler_list:
			return ()

		if event != namespace:
			_l = []
			for handler in handler_list:
				handler = getattr(handler, event, None)
				if handler:
					_l.append(handler)
			handler_list = tuple(_l)
		return handler_list

	def _event_handlers_in_namespace(self, event_handlers, event, namespace):
		# Ideally we'd cache these here, but event_handlers, as a dict,
		# is unhashable
		handler_list = event_handlers.get(namespace)
		return self.__event_handlers_for_event_in_namespace(
			tuple(handler_list) if handler_list else (),
			event,
			namespace )

	def _find_handler( self, event_handlers, session, message ):
		"""
		:return: A callable object of zero arguments, or None.
		"""
		event = message.get( 'name', '' )
		namespace = event
		if '_' in event:
			namespace = event[0:event.index('_')]
			event = event[event.index('_') + 1:]

		def l():
			logger.warning( "Dropping unhandled event '%s' from message %s", event, message )
		if not event:
			l()
			return

		handler_list = self._event_handlers_in_namespace(event_handlers, event, namespace)
		if not handler_list:
			l()
			return

		def call():
			"""
			Call the handlers in order, passing the arguments. The last non-None
			result from a handler will be our result. Any exception raised is propagated.
			"""
			last_result = None
			for h in handler_list:
				# Note that we're converting the input to objects for each
				# handler in the list. This could be a little inefficient in the case
				# of multiple handlers that come from related packages.
				__traceback_info__ = h, session, message
				args = _convert_message_args_to_objects( h, session, message )

				result = h(*args)
				if result is not None:
					last_result = result
			return last_result

		return call

	def _on_msg( self, event_handlers, session, message ):
		"""
		:return: Boolean value indicating success or failure.
		"""

		if message is None:
			# socket has died
			logger.debug( "Socket has died %s", session )
			return False
		if message.get('type') != 'event':
			logger.warning( 'Dropping unhandled message of wrong type %s', message )
			return False

		handler = self._find_handler( event_handlers, session, message ) # This logs missing handlers
		if handler is None:
			return False

		socket_obj = session.socket
		# We take a savepoint before running any handlers. We still need to
		# complete the transaction and commit it even if an exception occurs (because we have
		# handled this message; retrying won't help), but the work done
		# by the handlers should not be saved so as to ensure a consistent state.
		# Note that in ZODB, this causes the connection to do `cacheGC`, which
		# may or may not be a good thing
		savepoint = transaction.savepoint( optimistic=True )
		try:
			result = handler( )
			if message.get('id'):
				# they expect a response. Note that ack
				# is unlike 'send_event' and requires that the args be
				# pre-packed as an array. (This is due to how the JS expects
				# to find packet.args as an array)
				result = [toExternalObject(result)]
				socket_obj.ack( message['id'], result )
		except component.ComponentLookupError: # pragma: no cover
			# This is a programming error we can and should fix
			raise
		except (StandardError, Invalid) as e: # schema validation extends Invalid, and NOT StandardError
			savepoint.rollback() # could potentially raise InvalidSavepointRollbackError

			if ISocketEventHandlerClientError.providedBy( e ):
				error_type = 'client-error'
			else:
				error_type = 'server-error'
				logger.exception( "Exception handling event %s", message )

			event = _exception_to_event( e )
			event['error-type'] = error_type
			if message.get( 'id' ):
				socket_obj.ack( message['id'], [event] )
			else:
				socket_obj.send_event( error_type, json.dumps( event, sort_keys=__debug__ ) )
			return False
		else:
			return True

def _exception_to_event( the_error ):
	__traceback_info__ = the_error

	msg = ''

	if len(the_error.args) == 3:
		# message, field, value
		msg = the_error.args[0]

	# z3c.password and similar (nti.dataserver.users._InvalidData) set this for internationalization
	# purposes
	if getattr(the_error, 'i18n_message', None):
		msg = translate( the_error.i18n_message )
	else:
		msg = (the_error.args[0] if the_error.args else '') or msg
		# theoretically, translate can and will take any type of object,
		# but it needs to treat it as a "message id", and will use
		# that by default if no translation exists. That means it does a
		# unicode conversion, which, since this is an arbatrary object
		# might fail
		try:
			__traceback_info__ = msg
			# TODO: Rethink this, why were we trying to translate here?
			msg = translate(msg)
		except UnicodeDecodeError: #pragma: no cover
			msg = "Unknown error"
			logger.exception("What kind of error got us here? %r", the_error)

	return {'message': msg,
			'code': the_error.__class__.__name__ }

_registered_legacy_search_mods = set()

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from .interfaces import SocketSessionCreatedObjectEvent

def _convert_message_args_to_objects( handler, session, message ):
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
	for arg in message['args']:
		ext_factory = find_factory_for( arg )

		if ext_factory:
			v = ext_factory()
			notify( SocketSessionCreatedObjectEvent( v, session, message, arg ) )
			arg = update_from_external_object( v, arg )
		args.append( arg ) # strings and such fall through here

	return args
