#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The XHR polling transport.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from ZODB.loglevels import TRACE

import pyramid.interfaces
from .. import interfaces
from nti.dataserver import interfaces as nti_interfaces

from ._base import BaseTransport
from ._base import SessionEventProxy
from ._base import Empty
from ._base import decode_packet_to_session


import contextlib

@contextlib.contextmanager
def _using_session_proxy( service, sid  ):
	existing = service.get_proxy_session( sid )
	proxy = SessionEventProxy()
	if existing is None:
		service.set_proxy_session( sid, proxy )
		try:
			yield proxy
		finally:
			service.set_proxy_session( sid, None )
	else:
		logger.warn( "Session %s already has proxy %s", sid, existing )
		yield proxy


@component.adapter( pyramid.interfaces.IRequest )
@interface.implementer( interfaces.ISocketIOTransport )
class XHRPollingTransport(BaseTransport):

	proxy_timeout = 5.0

	def __init__(self, request):
		super(XHRPollingTransport, self).__init__(request)

	def options(self, session):
		rsp = self.request.response
		rsp.content_type = b'text/plain'
		return rsp

	def get(self, session):
		session.clear_disconnect_timeout()
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager
		result = None
		try:
			# A dead session will feed us a queue with a None object
			messages = session.get_messages_to_client()
			if messages is not None:
				messages = list(messages)
			if not messages:
				with _using_session_proxy( session_service, session.session_id ) as session_proxy:
					# Nothing to read right now.
					# The client expects us to block, though, for some time
					# We use our session proxy to both wait
					# and notify us immediately if a new message comes in
					session_proxy.get_client_msg( timeout=self.proxy_timeout )
					# Note that if we get a message via broadcast,
					# our cached session is going to be behind, so it's
					# pointless to try to read from it again. Unfortunately,
					# to avoid duplicate messages, we cannot just send
					# this one to the client (since its still in the session).
					# The simplest thing to do is to immediately return
					# and let the next poll pick up the message. Thus, the return
					# value is ignored and we simply wait
					# TODO: It may be possible to back out of the transaction
					# and retry.

			if not messages:
				raise Empty()
			# If we feed encode_multi None or an empty queue, it raises
			# ValueError.
			# If however, we feed it len() == 1 and that 1 is None,
			# it quietly returns None to us
			result = session.socket.protocol.encode_multi( messages )
		except (Empty,IndexError):
			result = session.socket.protocol.make_noop()

		__traceback_info__ = session, messages, result
		if result is None:
			# Must have pulled a None out of the queue. Which means our
			# session is dead. How to deal with this?
			logger.log( TRACE, "Polling got terminal None message. Need to disconnect." )
			result = session.socket.protocol.make_noop()

		response = self.request.response
		response.body = result
		return response

	def _request_body(self):
		return self.request.body


	def post(self, session, response_message=None):
		decode_packet_to_session( session, session.socket, self._request_body() )
		# The client will expect to re-confirm the session
		# by sending a blank post when it gets an error.
		# Our state must match. However, we cannot do this:
		# session.connection_confirmed = False
		# because our transaction is going to be rolled back

		response = self.request.response
		response.content_type = b'text/plain'
		response.headers[b'Connection'] = b'close'
		response.body = response_message or session.socket.protocol.make_noop()
		return response

	def _connect_response(self, session):
		response = self.request.response
		response.headers[b'Connection'] = b'close'
		response.body =  session.socket.protocol.make_connect()
		return response

	def connect(self, session, request_method ):
		if not session.connection_confirmed:
			# This is either the first time in,
			# or we've had an error that we detected. If it was an
			# error, then this could either be a POST
			# or a GET. We can handle GETs the same,
			# POSTs may have data (depending on if the
			# client thinks it should re-connect) that
			# need to be dealt with...
			session.connection_confirmed = True
			if request_method == b'POST' and self.request.content_length:
				response = self.post( session, response_message=session.socket.protocol.make_connect() )
			else:
				response = self._connect_response( session )
			return response

		if request_method == b'POST' and not self.request.content_length:
			# We have a session that WAS confirmed, but the client
			# thinks it is no longer confirmed...we're probably switching transports
			# due to a hard crash of an instance. So treat this
			# like a fresh connection
			response = self._connect_response( session )
			return response

		if request_method in (b"GET", b"POST", b"OPTIONS"):
			try:
				return getattr(self, request_method.lower())(session)
			except ValueError:
				# TODO: What if its binary data?
				logger.debug( "Failed to parse incoming body '%s'", self._request_body(), exc_info=True )
				raise

		raise Exception("No support for the method: " + request_method)
