#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for working with the :mod:`transaction` module.

This module depends on the :mod:`dm.transaction.aborthook` module
and directly provides the :func:`add_abort_hooks` function; you should
call this if you need such functionality.

"""
#$Id$

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

import transaction
import gevent.queue

from dm.transaction.aborthook import add_abort_hooks
add_abort_hooks = add_abort_hooks # pylint

import sys
import time

@interface.implementer(transaction.interfaces.IDataManager)
class ObjectDataManager(object):
	"""
	A generic (and therefore relatively expensive) :class:`transaction.interfaces.IDataManager`
	that invokes a callable (usually a method of an object) when the transaction finishes successfully.
	The method should not raise exceptions when invoked, as they will be caught and ignored
	(to preserve consistency with the rest of the data managers). If there's a chance the method could fail,
	then whatever actions it does take should not have side-effects.
	"""

	_EMPTY_KWARGS = {}

	def __init__(self, target=None, method_name=None, call=None, vote=None, args=(), kwargs=None):
		"""
		Construct a data manager. You must pass either the `target` and `method_name` arguments
		or the `call` argument. (You may always pass the `target` argument, which will
		be made available on this object for the use of :meth:`tpc_vote`. )

		:param target: An object. Optional if `call` is given.
		:param string method_name: The name of the attribute to get from `target`. Optional if `callable`
			is given.
		:param callable call: A callable object. Ignored if `target` *and* `method_name` are given.
		:param callable vote: If given, then a callable that will be called during the voting phase.
			It should raise an exception if the transaction will fail.
		:param args: A sequence of arguments to pass to the callable object. Optional.
		:param kwargs: A dictionary of arguments to pass to the callable object. Optional.
		"""
		self.target = target
		if method_name:
			self.callable = getattr( target, method_name )
		else:
			self.callable = call

		assert self.callable is not None

		self.args = args
		self.kwargs = kwargs or self._EMPTY_KWARGS

		self.vote = vote

		# Use the default thread transaction manager.
		self.transaction_manager = transaction.manager

	def commit(self, tx):
		pass

	def abort(self, tx):
		pass

	def sortKey(self):
		# We must not use our own ID, those aren't guaranteed
		# to be monotonically increasing, and we must be sorted
		# in the order we joined the transaction, for the queue property
		# (FIFO) to hold. The list.sort() is guaranteed to be stable,
		# so we can use the same key and we'll stay in the right order
		# It's not clearly documented, but this is supposed to be a string
		return str(id(self.target) if self.target is not None else id(self.callable))

	# No subtransaction support.
	def abort_sub(self, tx):
		pass  #pragma NO COVERAGE

	commit_sub = abort_sub

	def beforeCompletion(self, tx):
		pass  #pragma NO COVERAGE

	afterCompletion = beforeCompletion

	def tpc_begin(self, tx, subtransaction=False):
		assert not subtransaction

	def tpc_vote(self, tx):
		if self.vote:
			self.vote()

	def tpc_finish(self, tx):
		self.callable(*self.args, **self.kwargs)

	tpc_abort = abort

class _QueuePutDataManager(ObjectDataManager):
	"""
	A data manager that checks if the queue is full before putting.
	Overrides :meth:`tpc_vote` for efficiency.
	"""

	def __init__(self, queue, method, args=()):
		super(_QueuePutDataManager,self).__init__( target=queue, call=method, args=args )

	def tpc_vote(self, tx):
		if self.target.full():
			# TODO: Should this be a transient exception?
			# So retry logic kicks in?
			raise gevent.queue.Full()


def put_nowait( queue, obj ):
	"""
	Transactionally puts `obj` in `queue`. The `obj` will only be visible
	in the queue after the current transaction successfully commits.
	If the queue cannot accept the object because it is full, the transaction
	will be aborted.

	See :class:`gevent.queue.Queue` and :class:`Queue.Full` and :mod:`gevent.queue`.
	"""
	transaction.get().join(
		_QueuePutDataManager( queue,
							  queue.put_nowait,
							  args=(obj,) ) )

def do( *args, **kwargs ):
	"""
	Establishes a IDataManager in the current transaction.
	See :class:`ObjectDataManager` for the possible arguments.
	"""
	transaction.get().join(
		ObjectDataManager( *args, **kwargs ) )


def _do_commit( tx, description, long_commit_duration ):
	exc_info = sys.exc_info()
	try:
		duration = _timing( tx.commit, 'transaction.commit' )
		logger.debug( "Committed transaction for %s in %ss", description, duration )
		if duration > long_commit_duration: # pragma: no cover
			# We held (or attempted to hold) locks for a really, really, long time. Why?
			logger.warn( "Slow running commit for %s in %ss", description, duration )
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
from perfmetrics import Metric
def _timing( operation, name):
	"""
	Run the `operation` callable, returning the number of seconds it took.
	"""
	now = time.time()
	with Metric(name):
		operation()
	done = time.time()
	return done - now

class TransactionLoop(object):
	"""
	Similar to the transaction attempts mechanism, but less error prone and with added logging and
	hooks. This object is callable and runs its handler in the transaction loop.
	"""

	class AbortException(Exception):

		def __init__( self, response, reason ):
			Exception.__init__( self )
			self.response = response
			self.reason = reason


	sleep = None
	attempts = 10
	long_commit_duration = 6 # seconds

	def __init__( self, handler, retries=None, sleep=None, long_commit_duration=None ):
		self.handler = handler
		if retries is not None:
			self.attempts = retries + 1
		if long_commit_duration is not None:
			self.long_commit_duration = long_commit_duration
		if sleep is not None:
			self.sleep = sleep


	def prep_for_retry( self, number, *args, **kwargs ):
		"""
		Called just after a transaction begins if there will be
		more than one attempt possible. Do any preparation
		needed to cleanup or prepare reattempts, or raise
		self.AbortException.
		"""

	def should_abort_due_to_no_side_effects( self, *args, **kwargs ):
		"""
		Called after the handler has run. If the handler should
		have produced no side effects and the transaction can be aborted
		as an optimization, return True.
		"""
		return False

	def should_veto_commit( self, result, *args, **kwargs ):
		"""
		Called after the handler has run. If the result of the handler
		should abort the transaction, return True.
		"""
		return False

	def describe_transaction( self, *args, **kwargs ):
		return "Unknown"

	def run_handler( self, *args, **kwargs ):
		return self.handler( *args, **kwargs )

	def __call__( self, *args, **kwargs ):
		# NOTE: We don't handle repoze.tm being in the pipeline

		number = self.attempts
		note = self.describe_transaction( *args, **kwargs )

		while number:
			number -= 1
			try:
				tx = transaction.begin()
				if note and note != "Unknown":
					tx.note( note )
				if self.attempts != 1:
					self.prep_for_retry( number, *args, **kwargs )

				result = self.run_handler( *args, **kwargs )

				# We should still have the same transaction. If we don't,
				# then we get a ValueError from tx.commit.
				#assert transaction.get() is tx, "Started new transaction out from under us!"

				if self.should_abort_due_to_no_side_effects( *args, **kwargs ):
					# These transactions can safely be aborted and ignored, reducing contention on commit locks
					# TODO: It would be cool to open them readonly in the first place.
					# TODO: I don't really know if this is kosher, but it does seem to work so far
					# NOTE: We raise these as an exception instead of aborting in the loop so that
					# we don't retry if something goes wrong aborting
					raise self.AbortException( result, "side-effect free" )

				if tx.isDoomed() or self.should_veto_commit( result, *args, **kwargs ):
					raise self.AbortException( result, "doomed or vetoed" )

				_do_commit( tx, note, self.long_commit_duration )

				return result
			except self.AbortException as e:
				duration = _timing( transaction.abort, 'transaction.abort' )  # note: not our tx variable, whatever is current
				logger.debug( "Aborted %s transaction for %s in %ss", e.reason, note, duration )
				return e.response
			except Exception:
				exc_info = sys.exc_info()
				try:
					_timing( transaction.abort, 'transaction.abort' ) # note: not our tx variable, whatever is current
					retryable = transaction.manager._retryable(*exc_info[:-1])
					if number <= 0 or not retryable:
						raise
					if self.sleep:
						gevent.sleep( self.sleep )
				finally:
					del exc_info # avoid leak
