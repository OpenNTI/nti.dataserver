#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adds :class:`ZODB.interfaces.IExternalGC` support to (a limited
set of the databases configurations supported by) RelStorage.

Currently, this supports history-free storages (and is tested under mysql)
but other storages shouldn't be difficult.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from ZODB.interfaces import IExternalGC
from relstorage.storage import RelStorage
from relstorage.adapters.packundo import HistoryFreePackUndo
from ZODB.POSException import ReadOnlyError
from ZODB.POSException import StorageTransactionError

def _storage_deleteObject(self, oid, oldserial, transaction):
	if self._is_read_only:
		raise ReadOnlyError()
	# This is called in a phase of two-phase-commit (tpc).
	# This means we have a transaction, and that we are holding
	# the commit lock as well as the regular lock.
	# RelStorage native pack uses a separate pack lock, but
	# unfortunately there's no way to not hold the commit lock;
	# however, the transactions are very short.
	if transaction is not self._transaction:
		raise StorageTransactionError(self, transaction)

	# We don't worry about anything in self._cache because
	# by definition we are deleting objects that were
	# not reachable and so shouldn't be in the cache (or if they
	# were, we'll never ask for them anyway)

	# We delegate the actual operation to the adapter's packundo,
	# just like native pack
	cursor = self._store_cursor
	assert cursor is not None
	self._adapter.packundo.deleteObject(cursor, oid, oldserial)

	# When this is done, we get a tpc_vote,
	# and a tpc_finish.

	return

from ZODB.utils import u64

def _make_stmt(base,oid):
	return base % str(u64(oid))

def _historyFree_deleteObject(self, cursor, oid, oldserial):
	# The only things we need to worry about are
	# object_state and blob_chunk
	state = """
	DELETE FROM object_state
	WHERE zoid = %s
	"""
	chunk = """
	DELETE FROM blob_chunk
	WHERE zoid = %s
	"""

	self.runner.run_script_stmt(cursor, _make_stmt(state,oid))
	self.runner.run_script_stmt(cursor, _make_stmt(chunk,oid))


def _patch():


	if IExternalGC.implementedBy(RelStorage) or hasattr(RelStorage, 'deleteObject'):
		raise ImportError("Internals of RelStorage changed; check this patch")


	HistoryFreePackUndo.deleteObject = _historyFree_deleteObject
	RelStorage.deleteObject = _storage_deleteObject
	interface.classImplements(RelStorage, IExternalGC)

_patch()
del _patch
del _historyFree_deleteObject

def patch():
	pass
