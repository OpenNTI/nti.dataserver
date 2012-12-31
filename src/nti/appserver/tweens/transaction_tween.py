#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A tween that begins and ends transactions around its handler. This is initially
very similar to :mod:`pyramid_tm`, but with the following changes:

* The transaction is rolled back if the request is deemed to be side-effect free
  (this has intimate knowledge of the paths that do not follow the HTTP rules for a GET being side-effect free)

* Logging is added to account for the time spent in aborts and commits.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import time
import transaction

# Constants. pyramid_tm makes them configurable, but we don't
_LONG_COMMIT_DURATION = 6
_RETRIES = 10

def _commit_veto(request, response):
	"""
	When used as a commit veto, the logic in this function will cause the
	transaction to be aborted if:

	* An ``X-Tm`` response header with the value ``abort`` (or any value
	  other than ``commit``) exists.

	* The response status code starts with ``4`` or ``5``.

	Otherwise the transaction will be allowed to commit.
	"""
	xtm = response.headers.get('x-tm')
	if xtm is not None: # pragma: no cover
		return xtm != 'commit'
	return response.status.startswith(('4', '5'))

def _do_commit( request ):
	exc_info = sys.exc_info()
	try:
		duration = _timing( transaction.commit )
		logger.debug( "Committed transaction for %s in %ss", request.url, duration )
		if duration > _LONG_COMMIT_DURATION: # pragma: no cover
			# We held (or attempted to hold) locks for a really, really, long time. Why?
			logger.warn( "Slow running commit for %s in %ss", request.url, duration )
	except (AssertionError,ValueError): # pragma: no cover
		# We've seen this when we are recalled during retry handling. The higher level
		# is in the process of throwing a different exception and the transaction is
		# already toast, so this commit would never work, but we haven't lost anything;
		# The sad part is that this assertion error overrides the stack trace for what's currently
		# in progress
		# TODO: Prior to transaction 1.4.0, this was only an AssertionError. 1.4 makes it a ValueError, which is hard to distinguish and might fail retries?
		logger.exception( "Failing to commit; should already be an exception in progress" )
		if exc_info and exc_info[0]:
			raise exc_info[0], None, exc_info[2]

		raise
	## except ZODB.POSException.StorageError as e:
	## 	if str(e) == 'Unable to acquire commit lock':
	## 		# Relstorage locks. Who's holding it? What's this worker doing?
	## 		# if the problem is some other worker this doesn't help much.
	## 		# Of course by definition, we won't catch it in the act if we're running.
	## 		from ._util import dump_stacks
	## 		body = '\n'.join(dump_stacks())
	## 		print( body, file=sys.stderr )
	## 	raise

def _is_side_effect_free( request ):
	"""
	Is the request side-effect free? If the answer is yes, we should be able to quietly abort
	the transaction and avoid taking out any locks in the DBs.
	"""
	if request.method == 'GET':
		# GET requests must NEVER have side effects.
		if 'socket.io' in request.url:
			# (Unfortunately, socket.io polling does)
			# However, the static resources don't
			return True if 'static' in request.url else False

		return True
	# Every non-get probably has side effects
	return False

def _timing( operation ):
	"""
	Run the `operation` callable, returning the number of seconds it took.
	"""
	now = time.time()
	operation()
	done = time.time()
	return done - now

class _AbortException(Exception):

	def __init__( self, response, reason ):
		super(_AbortException,self).__init__( )
		self.response = response
		self.reason = reason

class _transaction_tween(object):

	__slots__ = ('handler',)

	def __init__( self, handler ):
		self.handler = handler

	def __call__( self, request ):
		# NOTE: We don't handle repoze.tm being in the pipeline

		number = _RETRIES

		while number:
			number -= 1
			try:
				transaction.begin()
				# make_body_seekable will copy wsgi.input if necessary,
				# otherwise it will rewind the copy to position zero
				if _RETRIES != 1:
					request.make_body_seekable()
				response = self.handler(request)


				if _is_side_effect_free( request ):
					# These transactions can safely be aborted and ignored, reducing contention on commit locks
					# TODO: It would be cool to open them readonly in the first place.
					# TODO: I don't really know if this is kosher, but it does seem to work so far
					# NOTE: We raise these as an exception instead of aborting in the loop so that
					# we don't retry if something goes wrong aborting
					raise _AbortException( response, "side-effect free" )

				if transaction.isDoomed() or _commit_veto( request, response ):
					raise _AbortException( response, "doomed or vetoed" )

				_do_commit( request )

				return response
			except _AbortException as e:
				duration = _timing( transaction.abort )
				logger.debug( "Aborted %s transaction for %s in %ss", e.reason, request.url, duration )
				return e.response
			except Exception:
				exc_info = sys.exc_info()
				try:
					transaction.abort()
					retryable = transaction.manager._retryable(*exc_info[:-1])
					if number <= 0 or not retryable:
						raise
				finally:
					del exc_info # avoid leak



def transaction_tween_factory(handler, registry):
	return _transaction_tween( handler )
