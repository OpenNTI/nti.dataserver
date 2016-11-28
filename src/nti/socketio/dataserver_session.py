#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An implementation of the session interface that offloads some
common operations from the database to the session manager.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.deprecation import deprecate

from nti.dataserver.interfaces import IDataserver

from nti.property.property import CachedProperty

from .session_consumer import SessionConsumer
from .persistent_session import AbstractSession

class Session(AbstractSession):
	"""
	Client session which checks the connection health and the queues for
	message passing.
	`self.owner`: An attribute for the user that owns the session.

	.. py:attribute:: originating_site_names

		The list of sites that apply to the request that created this session. Useful
		for applying site policies later on after the requests are gone.
	"""

	#originating_site_names = () # actually in the superclass for conflict resolution

	wsgi_app_greenlet = True # TODO: Needed anymore?

	heartbeat_is_transactional = False


	@deprecate("Prefer the `socket` property")
	def new_protocol( self, handler=None ):
		return self.socket

	@property
	@deprecate( "Prefer the `socket` property" )
	def protocol_handler(self):
		return self.socket

	@CachedProperty
	def message_handler(self):
		return SessionConsumer()

	# TODO: We want to ensure queue behaviour for
	# server messages across the cluster. Either that, or make the interaction
	# stateless
	def queue_message_from_client(self, msg):
		# Putting a server message immediately processes it,
		# wherever the session is loaded.
		self.message_handler( self, msg )

	def queue_message_to_client(self, msg):
		session_service = component.getUtility( IDataserver ).session_manager
		session_service.queue_message_to_client( self.session_id, msg )

	def get_messages_to_client(self):
		"""
		Returns an iterable of messages to the client, or possibly None if the session is dead. These messages
		are now considered consumed and cannot be retrieved by this method again.
		"""
		session_service = component.getUtility( IDataserver ).session_manager
		return session_service.get_messages_to_client( self.session_id )

	def clear_disconnect_timeout(self):
		session_service = component.getUtility( IDataserver ).session_manager
		session_service.clear_disconnect_timeout( self.session_id )

	@property
	def last_heartbeat_time(self):
		session_service = component.getUtility( IDataserver ).session_manager
		return session_service.get_last_heartbeat_time( self.session_id, self )

	def kill( self, send_event=True ):
		self.message_handler.kill(self)
		super(Session,self).kill(send_event=send_event)
