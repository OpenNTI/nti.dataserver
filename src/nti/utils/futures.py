#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility classes and objects for working with :mod:`concurrent.futures`.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools
import multiprocessing
import concurrent.futures

import platform
_is_pypy = platform.python_implementation() == 'PyPy'

def ConcurrentExecutor(max_workers=None):
	"""
	An abstraction layer to let code easily switch between different
	concurrency strategies. Import this instead of importing something
	from :mod:`concurrent.futures` directly.

	It also serves as a compatibility shim to make us compatible with
	gevent thread patching. For that reason, we avoid throwing any
	exceptions and instead return them, meaning that the caller should
	be prepared to get Exception objects in the results. This also
	means that for the multiprocessing case, the thrown exception
	needs to be properly pickleable. (Throwing exceptions from the
	called function is not safe in the multiprocessing case and can
	hang the pool, and has undefined results in the thread case.)

	.. note:: This strategy may change.
	"""

	# Notice that we did not import the direct class because it gets swizzled at
	# runtime. For that same reason, we subclass dynamically at runtime.
	if _is_pypy and False: # JAM: Why did I force pypy onto threaded workers?
		if max_workers is None:
			max_workers = multiprocessing.cpu_count()
		base = concurrent.futures.ThreadPoolExecutor
		throw = True
	else:
		base = concurrent.futures.ProcessPoolExecutor
		throw = False

	class _Executor(base):
		# map() channels through submit() so this captures all activity
		def submit( self, fn, *args, **kwargs ):
			_fn = _nothrow(fn, _throw=throw)
			_fn = functools.update_wrapper( _fn, fn )
			return super(_Executor,self).submit( _fn, *args, **kwargs )

	return _Executor(max_workers)

import pickle

class _nothrow(object):
	"""
	For submission to executors, a callable that doesn't throw (and
	avoids hangs.) Throwing used to result in hanging a process
	worker, but it may no longer be the case that it does in versions
	of :mod:`concurrent.futures` newer than 2.1.4. However,
	we still provide useful printing.

	For pickling, must be a top-level object.
	"""

	def __init__(self, fn, _throw=False):
		self.__fn = fn
		self.__throw = _throw

	def __call__( self, *args, **kwargs):
		try:
			return self.__fn(*args, **kwargs)
		except Exception as e:
			# logging may not be reliable in this pool
			from zope.exceptions import print_exception
			import sys
			print_exception( *sys.exc_info() )
			if self.__throw:
				raise
			# We'd like to return something useful, but
			# the exception itself may not be serializable
			# (and usually isn't if it has arguments and is an
			# Exception subclass---see the Python bug about this)
			try:
				pickle.loads(pickle.dumps(e))
			except Exception:
				return Exception(str(e))
			else:
				return e
