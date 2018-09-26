#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common or base implementation support code for transports.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import transaction

from zope import component

from ZODB.loglevels import TRACE

from nti.externalization.persistence import NoPickle

from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.transactions import transactions

try:
	from gevent import Greenlet
	from gevent import sleep
	from gevent.queue import Queue
except ImportError:
	from Queue import Queue
	from greenlet import greenlet as Greenlet
	from time import sleep

sleep = sleep
Queue = Queue
Greenlet = Greenlet

from Queue import Empty
Empty = Empty

@NoPickle
class BaseTransport(object):
	"""Base class for all transports. Mostly wraps handler class functions."""

	def __init__(self, request):
		"""
		:param request: A :class:`pyramid.request.Request` object.
		"""
		self.request = request

	def kill(self):
		pass

def catch_all(greenlet):
	def f(*args):
		try:
			greenlet(*args)
		except:
			# Trap and log.
			# We no longer expect to use GreenletExit, so it isn't handled
			# specially.
			logger.exception( "Failed to run greenlet %s", greenlet )
	return f

def decode_packet_to_session( session, sock, data, doom_transaction=True ):
	try:
		pkts = sock.protocol.decode_multi( data )
	except ValueError:
		# Bad data from the client. This will never work
		if doom_transaction:
			transaction.doom()
		raise

	for pkt in pkts:
		if pkt.msg_type == 0:
			safe_kill_session( session, "on receipt of death packet %s from remote client" % pkt )
		elif pkt.msg_type == 1:
			sock.send_connect( pkt['data'] )
		elif pkt.msg_type == 2: # heartbeat
			session.heartbeat()
		else:
			#logger.debug( "Session %s received msg %s", session, pkt )
			session.queue_message_from_client( pkt )

def safe_kill_session( session, reason='' ):
	logger.log( TRACE, "Killing session %s %s", session, reason )
	try:
		session.kill()
	except AttributeError:
		pass
	except:
		logger.exception( "Failed to kill session %s", session )

def run_job_in_site( *args, **kwargs ):
	runner = component.getUtility( IDataserverTransactionRunner )
	return runner( *args, **kwargs )

@NoPickle
class SessionEventProxy(object):
	"""
	Can be used as a session proxy for getting events when
	broadcast messages arrive.

	Functions in a transaction-aware manner for putting client messages
	to avoid them getting put multiple times in the event of retries.
	"""

	def __init__(self):
		# This queue should be unbounded, otherwise we could
		# cause commit problems
		self.client_queue = Queue()

	def get_client_msg(self, **kwargs):
		return self.client_queue.get(**kwargs)

	def queue_message_to_client(self, msg):
		transactions.put_nowait(self.client_queue, msg)
