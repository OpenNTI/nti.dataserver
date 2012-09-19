#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module, which requires gevent >= 1.0b4, patches the system on import
to use event-driven functions. Obviously that's an import-time side effect,
hence the unwieldy name.

If this is imported too late and we know that things will not work, we raise an exception.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"


import sys

import gevent
import gevent.monkey
TRACE_GREENLETS = False

if getattr( gevent, 'version_info', (0,) )[0] >= 1 and 'ZEO' not in sys.modules: # Don't do this when we are loaded for conflict resolution into somebody else's space

	import gevent.os
	try:
		gevent.os.__all__.remove('read')
		gevent.os.__all__.remove('write')
	except ValueError:
		# As of 1.0b4/2012-09-11, os.read and os.write are patched to
		# operate in non-blocking mode when os is patched. Part of this non-blocking
		# activity is to catch OSError with errno == EAGAIN, since non-blocking descriptors
		# will raise EAGAIN when there is nothing to read. However, this breaks if the process
		# was already expecting to do non-blocking IO and expecting to handle EAGAIN: It no longer
		# gets these exceptions and may find itself trapped in an infinite loop. Such is the
		# case with gunicorn.arbitrer. One symptom is that the master doesn't exit on a ^C (as signal
		# handling is tied to reading from a non-blocking pipe).
		logger = __import__('logging').getLogger(__name__) # Only import this after the patch, it allocates locks
		logger.exception( "Failed to remove os.read/write patch. Gevent outdated?")
		raise

	# NOTE: There is an incompatibility with patching 'thread' and the 'multiprocessing' module:
	gevent.monkey.patch_all()
	logger = __import__('logging').getLogger(__name__) # Only import this after the patch, it allocates locks
	logger.info( "Monkey patching most libraries for gevent" )
	# The problem is that multiprocessing.queues.Queue uses a half-duplex multiprocessing.Pipe,
	# which is implemented with os.pipe() and _multiprocessing.Connection. os.pipe isn't patched
	# by gevent, as it returns just a fileno. _multiprocessing.Connection is an internal implementation
	# class implemented in C, which exposes a 'poll(timeout)' method; under the covers, this issues a
	# (blocking) select() call: hence the need for a real thread. Except for that method, we could
	# almost replace Connection with gevent.fileobject.SocketAdapter, plus a trivial
	# patch to os.pipe (below). Sigh, so close. (With a little work, we could replicate that method)

	# import os
	# import fcntl
	# os_pipe = os.pipe
	# def _pipe():
	#	r, w = os_pipe()
	#	fcntl.fcntl(r, fcntl.F_SETFL, os.O_NONBLOCK)
	#	fcntl.fcntl(w, fcntl.F_SETFL, os.O_NONBLOCK)
	#	return r, w
	#os.pipe = _pipe

	# However, there is a more serious conflict. We MUST have greenlet local things like
	# transactions. We can do that with some careful patching. But then we must have
	# greenlet-aware locks. If we patch them as well, then the ProcessPoolExecutor fails.
	# Basically there's a conflict between multiprocessing and greenlet locks, or Real threads
	# and greenlet locks.
	# So it turns out to be easier to patch the ProcessPoolExecutor to use "threads"
	# and patch the threading system.
	import gevent.local
	import threading

	_threading_local = __import__('_threading_local')

	import concurrent.futures
	import multiprocessing
	# Stash the original
	setattr( concurrent.futures, '_ProcessPoolExecutor', concurrent.futures.ProcessPoolExecutor )
	def ProcessPoolExecutor( max_workers=None ):
		if max_workers is None:
			max_workers = multiprocessing.cpu_count()
		return concurrent.futures.ThreadPoolExecutor( max_workers )
	concurrent.futures.ProcessPoolExecutor = ProcessPoolExecutor

	# Patch for try/finally missing in ZODB 3.10.5 that can lead to deadlock
	# See https://bugs.launchpad.net/zodb/+bug/1048644
	def tpc_begin(self, txn, tid=None, status=' '):
		"""Storage API: begin a transaction."""
		if self._is_read_only:
			raise POSException.ReadOnlyError()
		#logger.debug( "Taking tpc lock %s %s for %s", self, self._tpc_cond, txn )
		self._tpc_cond.acquire()
		try:
			self._midtxn_disconnect = 0
			while self._transaction is not None:
				# It is allowable for a client to call two tpc_begins in a
				# row with the same transaction, and the second of these
				# must be ignored.
				if self._transaction == txn:
					raise POSException.StorageTransactionError(
						"Duplicate tpc_begin calls for same transaction")

				self._tpc_cond.wait(30)
		finally:
			#logger.debug( "Releasing tpc lock %s %s for %s", self, self._tpc_cond, txn )
			self._tpc_cond.release()

		self._transaction = txn

		try:
			self._server.tpc_begin(id(txn), txn.user, txn.description,
								   txn._extension, tid, status)
		except:
			# Client may have disconnected during the tpc_begin().
			if self._server is not disconnected_stub:
				self.end_transaction()
			raise

		self._tbuf.clear()
		self._seriald.clear()
		del self._serials[:]
	import ZEO.ClientStorage
	ZEO.ClientStorage.ClientStorage.tpc_begin = tpc_begin


	# The dummy-thread deletes __block, which interacts
	# badly with forking process with subprocess: after forking,
	# Thread.__stop is called, which throws an exception
	orig_stop = getattr( threading.Thread, '_Thread__stop' )
	def __stop(self):
		if hasattr( self, '_Thread__block' ):
			orig_stop( self )
		else:
			setattr( self, '_Thread__stopped', True )
	setattr( threading.Thread, '_Thread__stop', __stop )



	# depending on the order of imports, we may need to patch
	# some things up manually.
	# NOTE: This list is not complete.
	# NOTE: These things are critical to the operation of the system,
	# so if they aren't patched due to a bad import order, we
	# bail
	import transaction
	if gevent.local.local not in transaction.ThreadTransactionManager.__bases__:
		raise TypeError( "Transaction package not monkey patched. Bad import order" )

	import zope.component
	import zope.component.hooks
	if gevent.local.local not in type(zope.component.hooks.siteinfo).__bases__:
		raise TypeError( "zope.component package not monkey patched. Bad import order" )

	# Patch the logging package to be aware of greenlets and format things
	# nicely
	import logging
	from logging import LogRecord
	from gevent import getcurrent, Greenlet
	class _LogRecord(LogRecord):
		def __init__( self, *args, **kwargs ):
			LogRecord.__init__( self, *args, **kwargs )
			# TODO: Respect logging.logThreads?
			if self.threadName and (self.threadName == 'MainThread' or self.threadName.startswith( 'Dummy-' )):
				current = getcurrent()
				thread_info = getattr( current, '__thread_name__', None )
				if thread_info:
					self.thread = id(current)
					self.threadName = thread_info()

				elif type(current) == Greenlet \
				  or isinstance( current, Greenlet ):
					self.thread = id( current )
					self.threadName = current._formatinfo()

	logging.LogRecord = _LogRecord

	if TRACE_GREENLETS:
		import greenlet
		def greenlet_trace( event, origin ):
			print( "Greenlet switching from", event, "to", origin, file=sys.stderr )
		greenlet.settrace( greenlet_trace )

	del _LogRecord
	del zope
	del transaction
	del threading
	del _threading_local
else:
	logger = __import__('logging').getLogger(__name__)
	logger.info( "Not monkey patching any gevent libraries" )


# Monkey-patch for RelStorage to use pure-python drivers that are non-blocking
try:
	logger.debug( "Attempting MySQL monkey patch" )
	import umysqldb
except ImportError as e:
	logger.exception( "Please 'pip install -r requirements.txt' to get non-blocking drivers." )
	# This early, logging is probably not set up
	import traceback
	print( "Please 'pip install -r requirements.txt' to get non-blocking drivers.", file=sys.stderr )
	traceback.print_exc( e )
else:
	logger.info( "Monkey-patching the MySQL driver for RelStorage to work with gevent" )

	umysqldb.install_as_MySQLdb()

	# The underlying umysql driver doesn't handle dicts as arguments
	# to queries (as of 2012-09-13). Until it does, we need to do that
	# because RelStorage uses that in a few places

	import umysqldb.connections
	from umysqldb.connections import encoders, notouch
	class Connection(umysqldb.connections.Connection):

		def query( self, sql, args=() ):
			__traceback_info__ = args
			if isinstance( args, dict ):
				# First, encode them as strings
				args = {k: encoders.get(type(v), notouch)(v) for k, v in args.items()}
				# now format the string
				sql = sql % args
				# and delete the now useless args
				args = ()
			super(Connection,self).query( sql, args=args )

	# Patching the module itself seems to be not needed because
	# RelStorage uses 'mysql.Connect' directly. And if we patch the module,
	# we get into recursive super calls
	#umysqldb.connections.Connection = Connection
	# Also patch the re-export of it
	umysqldb.connect = Connection
	umysqldb.Connection = Connection
	umysqldb.Connect = Connection

def patch():
	pass
