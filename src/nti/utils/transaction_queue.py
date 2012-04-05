#!/usr/bin/env python
"""
Provides transaction-aware methods to operate on queues (specifically,
	:class:`gevent.queue.Queue`).
"""
#$Id$
from zope import interface

import transaction
import gevent.queue

class _QueuePutDataManager(object):
	"""
	A data manager that checks if the queue is full before putting.
	"""
	interface.implements(transaction.interfaces.IDataManager)

	def __init__(self, queue, method, args=()):
		self.queue = queue
		self.callable = method
		self.args = args
		# Use the default thread transaction manager.
		self.transaction_manager = transaction.manager

	def commit(self, tx):
		pass

	def abort(self, tx):
		pass

	def sortKey(self):
		return id(self)

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
		if self.queue.full():
			# TODO: Should this be a transient exception?
			# So retry logic kicks in?
			raise gevent.queue.Full()

	def tpc_finish(self, tx):
		self.callable(*self.args)

	tpc_abort = abort

def put_nowait( queue, obj ):
	"""
	Transactionally puts `obj` in `queue`. The `obj` will only be visible
	in the queue after the current transaction successfully commits.
	If the queue cannot accept the object because it is full, the transaction
	will be aborted.
	"""
	transaction.get().join(
		_QueuePutDataManager( queue,
							  queue.put_nowait,
							  args=(obj,) ) )
