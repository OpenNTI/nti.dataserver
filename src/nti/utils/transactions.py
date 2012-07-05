#!/usr/bin/env python
"""
Support for working with the :mod:`transaction` module.
"""
#$Id$
from zope import interface

import transaction
import gevent.queue

class ObjectDataManager(object):
	"""
	A generic (and therefore relatively expensive) :class:`transaction.interfaces.IDataManager`
	that invokes a callable (usually a method of an object) when the transaction finishes successfully.
	The method should not raise exceptions when invoked, as they will be caught and ignored
	(to preserve consistency with the rest of the data managers). If there's a chance the method could fail,
	then whatever actions it does take should not have side-effects.
	"""
	interface.implements(transaction.interfaces.IDataManager)

	_EMPTY_KWARGS = {}

	def __init__(self, target=None, method_name=None, call=None, vote=None, args=(), kwargs=None):
		"""
		Construct a data manager. You must pass either the `target` and `method_name` arguments
		or the `call` argument. (You may always pass the `target` argument, which will
		be made available on this object for the use of :meth:`tpc_vote`. )

		:param target: An object. Optional if `callable` is given.
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
		return id(self.target) if self.target is not None else id(self.callable)

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
	interface.implements(transaction.interfaces.IDataManager)

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
