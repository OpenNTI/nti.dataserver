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

# All the patching uses private things so turn that warning off
#pylint: disable=W0212
import sys

import gevent
import gevent.monkey
TRACE_GREENLETS = False

def _patch_process_pool_executor():

	import concurrent.futures
	import multiprocessing
	# Stash the original
	setattr( concurrent.futures, '_ProcessPoolExecutor', concurrent.futures.ProcessPoolExecutor )
	def ProcessPoolExecutor( max_workers=None ):
		if max_workers is None:
			max_workers = multiprocessing.cpu_count()
		return concurrent.futures.ThreadPoolExecutor( max_workers )
	concurrent.futures.ProcessPoolExecutor = ProcessPoolExecutor

def _patch_zeo_client_storage_deadlock():
	# Patch for try/finally missing in ZODB 3.10.5/3.11.0a1 ZEO4.0.0a1 that can lead to deadlock
	# See https://bugs.launchpad.net/zodb/+bug/1048644
	# See https://github.com/zopefoundation/ZEO/pull/1
	from ZODB import POSException
	import ZEO.ClientStorage
	from ZEO.ClientStorage import disconnected_stub

	def tpc_begin(self, txn, tid=None, status=' '):
		"""Storage API: begin a transaction."""
		if self._is_read_only:
			raise POSException.ReadOnlyError()
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

	ZEO.ClientStorage.ClientStorage.tpc_begin = tpc_begin

def _patch_thread_stop():
	# The dummy-thread deletes __block, which interacts
	# badly with forking process with subprocess: after forking,
	# Thread.__stop is called, which throws an exception
	orig_stop = getattr( threading.Thread, '_Thread__stop' )
	def __stop(self):
		if hasattr( self, '_Thread__block' ):

			# Now kill the greenlet that's running this thread
			# In a pthread scenario, the threads die on the fork, so
			# this is basically the same thing...they just get a chance
			# to cleanup because of GreenletExit.
			# We don't need to do this for the main thread, or if
			# we are dead in the normal process and not during a fork
			caller = sys._getframe( 1 )

			if self.name != 'MainThread' and caller.f_locals.get( 'self' ) is not self:
				greenlet_id = self.ident
				import gc
				def _make_kill( x ):
					def k():
						x.throw()
						orig_stop( self )
					return k
				for ob in gc.get_objects():
					if id(ob) == greenlet_id and hasattr( ob, 'throw' ):
						#print( "Thread", self, "killing running greenlet", x )
						# Note that since this is after a fork, and the fork process replaces
						# threading._active, the gevent _DummyThread's cleanup process will
						# throw KeyErrors that get printed on stderr
						gevent.spawn_later( 0.1, run=_make_kill(ob) )
						break
			else:
				orig_stop( self )
		else:
			setattr( self, '_Thread__stopped', True )


	setattr( threading.Thread, '_Thread__stop', __stop )

def _patch_logging():
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


def check_threadlocal_status(names=('transaction.ThreadTransactionManager', 'zope.component.hooks.siteinfo', 'pyramid.threadlocal.ThreadLocalManager', 'pyramid.threadlocal.manager')):
	# depending on the order of imports, we may need to patch
	# some things up manually.
	# NOTE: This list is not complete.
	# NOTE: These things are critical to the operation of the system,
	# so if they aren't patched due to a bad import order, we
	# bail
	import zope.dottedname.resolve as dottedname
	for name in names:
		try:
			obj = dottedname.resolve(name)
		except ImportError:
			logger.debug( "Not checking gevent status of %s", name, exc_info=True )
			continue

		if not isinstance(obj, type):
			obj = type(obj)
		logger.debug( "Checking gevent status of %s=%s: %s", name, obj, obj.__bases__ )
		#print( name, obj, obj.__bases__ )
		if gevent.local.local not in obj.__bases__:
			raise TypeError( "%s not monkey patched. Bad import order" % name )


if getattr( gevent, 'version_info', (0,) )[0] >= 1 and 'ZEO' not in sys.modules: # Don't do this when we are loaded for conflict resolution into somebody else's space

	# As of 2012-10-30 and gevent 1.0rc1, the change in 1.0b4 to patch os.read and os.write
	# is undone. Comments below left for historical interest

	# The below is fixed as of 2012-09-21. If pserve hangs on a signal, you need to update.
	# This will be deleted in a few weeks.
	# import gevent.os
	# try:
	# 	gevent.os.__all__.remove('read')
	# 	gevent.os.__all__.remove('write')
	# except ValueError:
	# 	# As of 1.0b4/2012-09-11, os.read and os.write are patched to
	# 	# operate in non-blocking mode when os is patched. Part of this non-blocking
	# 	# activity is to catch OSError with errno == EAGAIN, since non-blocking descriptors
	# 	# will raise EAGAIN when there is nothing to read. However, this breaks if the process
	# 	# was already expecting to do non-blocking IO and expecting to handle EAGAIN: It no longer
	# 	# gets these exceptions and may find itself trapped in an infinite loop. Such is the
	# 	# case with gunicorn.arbitrer. One symptom is that the master doesn't exit on a ^C (as signal
	# 	# handling is tied to reading from a non-blocking pipe).
	# 	logger = __import__('logging').getLogger(__name__) # Only import this after the patch, it allocates locks
	# 	logger.exception( "Failed to remove os.read/write patch. Gevent outdated?")
	# 	raise

	# As of 2012-10-06, patching sys/std[out/err/in] hangs gunicorn, so be sure it's false (this is marked experimental in 1.0rc1)
	gevent.monkey.patch_all(subprocess=True, sys=False, Event=False)

	# NOTE: There is an incompatibility with patching 'thread' and the 'multiprocessing' module:
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
	# and let gevent patch the threading system.

	# Now that that's done, we can import some other things:

	logger = __import__('logging').getLogger(__name__) # Only import this after the patch, it allocates locks
	logger.info( "Monkey patching most libraries for gevent" )

	import gevent.local
	import threading
	_threading_local = __import__('_threading_local') # TODO: Why is this imported now?

	# And now the things to patch ProcessPoolExecutor as described
	_patch_process_pool_executor()

	_patch_zeo_client_storage_deadlock()

	_patch_thread_stop()

	check_threadlocal_status()

	_patch_logging()

	if TRACE_GREENLETS:
		import greenlet
		def greenlet_trace( event, origin ):
			print( "Greenlet switching from", event, "to", origin, file=sys.stderr )
		greenlet.settrace( greenlet_trace )

	# We monkey patched threads out of the way, so there's
	# no need for the GIL checking for thread switches. Turn it
	# way down to reduce its overhead (default 100
		_CHECK_INTERVAL = 10000
		if sys.getcheckinterval() < _CHECK_INTERVAL:
			sys.setcheckinterval( _CHECK_INTERVAL )

	del threading
	del _threading_local


	logger.info( "Monkey-patching the MySQL driver for RelStorage to work with gevent" )

	# Monkey-patch for RelStorage to use pure-python drivers that are non-blocking
	from . import relstorage_umysqldb_patch_on_import
	relstorage_umysqldb_patch_on_import.patch()

else:
	logger = __import__('logging').getLogger(__name__)
	logger.info( "Not monkey patching any gevent libraries" )

def patch():
	pass
