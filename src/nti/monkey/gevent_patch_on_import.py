#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module, which requires gevent >= 1.0b4, patches the system on import
to use event-driven functions. Obviously that's an import-time side effect,
hence the unwieldy name.

If this is imported too late and we know that things will not work, we raise an exception.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# DO NOT create a logger at the top of this file;
# it allocates locks
#logger = __import__('logging').getLogger(__name__)

# All the patching uses private things so turn that warning off
# pylint: disable=W0212
import sys

import gevent
import gevent.monkey
TRACE_GREENLETS = False

def _patch_process_pool_executor():

	import multiprocessing
	import concurrent.futures

	# Stash the original
	setattr(concurrent.futures,
			'_ProcessPoolExecutor',
			concurrent.futures.ProcessPoolExecutor )

	def ProcessPoolExecutor( max_workers=None ):
		if max_workers is None:
			max_workers = multiprocessing.cpu_count()
		return concurrent.futures.ThreadPoolExecutor( max_workers )
	concurrent.futures.ProcessPoolExecutor = ProcessPoolExecutor

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
	# Patch the logging package to be aware of greenlets and format
	# things nicely. The default logging Formatter object simply takes
	# the __dict__ of the record and applies it to the format string,
	# so any information must be reified, not properties.

	import logging
	from logging import LogRecord
	from gevent import getcurrent

	# The logging module defines a bunch of undocumented (just commented)
	# constants like 'logThreads', 'logProcesses' and 'logMultiprocessing'
	# These are all true by default, and control, respectively, the
	# thread/threadName, process (aka pid) and processName attributes.

	class _LogRecord(LogRecord):

		def __init__( self, *args, **kwargs ):
			LogRecord.__init__( self, *args, **kwargs )

			if not self.threadName:
				# logger.logThreads was set to False probably
				return

			if (self.threadName == 'MainThread'
				or self.threadName.startswith( 'Dummy-' )):

				current = getcurrent()
				# We define __thread_name__ in our custom greenlet worker
				# subclass (see nti.appserver.nti_gunicorn); _formatinfo is
				# an internal debugging method from gevent
				thread_info = (getattr(current, '__thread_name__', None)
							   or getattr(current, '_formatinfo', None))
				if thread_info:
					self.thread = id(current)
					self.threadName = thread_info()

	logging.LogRecord = _LogRecord

def _patch_memcache():
	"""
	The pure-python memcache client wants to make *everything*
	in its __dict__ greenlet local, including all sockets.

	While generally that might be an acceptable solution, it fails
	when there are many long-lived greenlets that might use the
	object. We have that situation with our websocket connections.

	Our primary use of memcache is through ZODB/RelStorage, where it
	maintains a one-to-one mapping between connections and memcache
	Client objects. ZODB/RelStorage connections are single
	thread/greenlet objects, so having the sockets be greenlet local
	is no benefit. In fact, it is a net loss, leading to far too many
	extent sockets.

	Therefore, we go to some pains here to make the memcache implementation
	NOT greenlet local.
	"""
	# We cannot change the base after the fact because of the use of __new__,
	# so we must carefully manage the order of imports.
	import threading
	local = threading.local
	try:
		threading.local = object
		import memcache
		assert memcache.Client.__bases__ == (object,)
	finally:
		threading.local = local

def check_threadlocal_status(names=('transaction.ThreadTransactionManager',
									'zope.component.hooks.siteinfo',
									'pyramid.threadlocal.ThreadLocalManager',
									'pyramid.threadlocal.manager')):
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

	# Now the rlock patch for ZODB
	dottedname.resolve('ZODB.DB')
	db = sys.modules['ZODB.DB'] # ZODB.DB shadows the module
	if db.threading.RLock is not gevent.lock.RLock:
		raise TypeError("ZODB.DB/threading.RLock not monkey patched")

# XXX: This is fixed in https://github.com/gevent/gevent/pull/546,
# https://github.com/gevent/gevent/pull/551 and 552. We should switch
# to one of those branches (552 is required for pypy.)
def new_ssl_init():

	import errno

	from ssl import SSLContext
	from ssl import SOL_SOCKET, SO_TYPE
	from ssl import AF_INET, SOCK_STREAM

	from gevent.ssl import CERT_NONE
	from gevent.ssl import PROTOCOL_SSLv23
	from gevent.socket import socket, error as socket_error

	_delegate_methods = ('recv', 'recvfrom', 'recv_into', 'recvfrom_into', 'send', 'sendto')

	def sslsock_init(self, sock=None, keyfile=None, certfile=None,
				 server_side=False, cert_reqs=CERT_NONE,
				 ssl_version=PROTOCOL_SSLv23, ca_certs=None,
				 do_handshake_on_connect=True,
				 family=AF_INET, type=SOCK_STREAM, proto=0, fileno=None,
				 suppress_ragged_eofs=True, npn_protocols=None, ciphers=None,
				 server_hostname=None,
				 _context=None):

		if _context:
			self._context = _context
		else:
			if server_side and not certfile:
				raise ValueError("certfile must be specified for server-side "
								 "operations")
			if keyfile and not certfile:
				raise ValueError("certfile must be specified")
			if certfile and not keyfile:
				keyfile = certfile
			self._context = SSLContext(ssl_version)
			self._context.verify_mode = cert_reqs
			if ca_certs:
				self._context.load_verify_locations(ca_certs)
			if certfile:
				self._context.load_cert_chain(certfile, keyfile)
			if npn_protocols:
				self._context.set_npn_protocols(npn_protocols)
			if ciphers:
				self._context.set_ciphers(ciphers)
			self.keyfile = keyfile
			self.certfile = certfile
			self.cert_reqs = cert_reqs
			self.ssl_version = ssl_version
			self.ca_certs = ca_certs
			self.ciphers = ciphers
		# Can't use sock.type as other flags (such as SOCK_NONBLOCK) get
		# mixed in.
		if sock.getsockopt(SOL_SOCKET, SO_TYPE) != SOCK_STREAM:
			raise NotImplementedError("only stream sockets are supported")

		# CPython: XXX: Must pass the underlying socket, not our
		# potential wrapper; test___example_servers fails the SSL test
		# with a client-side EOF error. (Why?)
		socket.__init__(self, _sock=sock._sock)

		# The initializer for socket overrides the methods send(), recv(), etc.
		# in the instancce, which we don't need -- but we want to provide the
		# methods defined in SSLSocket.
		for attr in _delegate_methods:
			try:
				delattr(self, attr)
			except AttributeError:
				pass
		if server_side and server_hostname:
			raise ValueError("server_hostname can only be specified "
							 "in client mode")
		self.server_side = server_side
		self.server_hostname = server_hostname
		self.do_handshake_on_connect = do_handshake_on_connect
		self.suppress_ragged_eofs = suppress_ragged_eofs
		self.settimeout(sock.gettimeout())

		# See if we are connected
		try:
			self.getpeername()
		except socket_error as e:
			if e.errno != errno.ENOTCONN:
				raise
			connected = False
		else:
			connected = True

		self._makefile_refs = 0
		self._closed = False
		self._sslobj = None
		self._connected = connected
		if connected:
			# create the SSL object
			try:
				self._sslobj = self._context._wrap_socket(self._sock, server_side,
														  server_hostname, ssl_sock=self)
				if do_handshake_on_connect:
					timeout = self.gettimeout()
					if timeout == 0.0:
						# non-blocking
						raise ValueError("do_handshake_on_connect should not be specified for non-blocking sockets")
					self.do_handshake()

			except socket_error as x:
				self.close()
				raise x

	return sslsock_init

version_info = getattr( gevent, 'version_info', (0, 0, 0, 'final', 0))

def _patch_ssl():
	import platform
	is_pypy = platform.python_implementation() == 'PyPy'
	if is_pypy:
		# If we're running this on pypy, we have a fixed branch
		# anyway
		return

	if version_info[0:3] == (1, 0, 1) and sys.version_info[0:3] >= (2,7,9):
		logger.info( "Monkey-patching the SSLSocket" )
		from gevent.ssl import SSLSocket
		SSLSocket.__init__ = new_ssl_init()

# Don't do this when we are loaded for conflict resolution into somebody else's space
if version_info[0] >= 1 and 'ZEO' not in sys.modules:

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

	# As of 2012-10-06, patching sys/std[out/err/in] hangs gunicorn, so be sure it's false
	# (this is marked experimental in 1.0rc1)
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

	import threading
	# Gevent patches the primitives that make up threading.RLock,
	# but leaves RLock in place. This is nice if it has already
	# been imported. However, it is cleaner to replace it if it hasn't
	# been. So we do that.
	import gevent.lock
	assert threading.RLock is not gevent.lock.RLock # in case internals change
	gevent.monkey.saved['threading']['RLock'] = threading.RLock
	threading.RLock = gevent.lock.RLock

	import gevent.local
	_threading_local = __import__('_threading_local') # TODO: Why is this imported now?

	# And now the things to patch ProcessPoolExecutor as described
	# TODO: What about the ``gipc`` project? It has a Process object compatible
	# with multiprocessing's Process object (and it already has some monkey
	# patches for multiprocessing), maybe we can use it here?
	_patch_process_pool_executor()

	_patch_thread_stop()

	check_threadlocal_status()

	_patch_logging()

	_patch_memcache()

	_patch_ssl()

	if TRACE_GREENLETS:
		import greenlet
		def greenlet_trace( event, origin ):
			print( "Greenlet switching from", event, "to", origin, file=sys.stderr )
		greenlet.settrace( greenlet_trace )

	# We monkey patched threads out of the way, so there's no need for
	# the GIL checking for thread switches. However, it is still
	# needed for signal handling, and some versions of gevent do
	# internally use a separate thread. So turn it down but not too
	# far down to reduce its overhead (default 100)
	_CHECK_INTERVAL = 1000
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
