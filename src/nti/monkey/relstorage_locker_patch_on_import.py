#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Patch some issues in relstorage's locker module: proved a better
error when commit locking fails, and track the time that a lock is
held (in mysql).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from relstorage.adapters import locker

if not hasattr(locker, 'StorageError'):
	raise ImportError("locker changed, check compatibility")

_OrigStorageError = locker.StorageError

from nti.zodb.interfaces import UnableToAcquireCommitLock

def _StorageError(msg):
	if 'commit lock' in msg:
		return UnableToAcquireCommitLock(msg)
	return _OrigStorageError(msg)

import time

LONG_LOCK_TIME = 5 # seconds

def _patch_hold_logging(cls):

	cls.locked_at = 0

	orig_hold = cls.hold_commit_lock
	orig_release = cls.release_commit_lock

	# depending on the 'nowait' argument, locking
	# will either return a boolean (if true)
	# or raise a storage error (if locking failed) or None (if locking worked)
	# There can be priority inversions here because this lock
	# is totally out of gevent/threadings control; it would almost
	# be nice to raise our priority or even stop task switching
	# altogether while we hold this.
	def hold_commit_lock(self, *args, **kwargs):
		try:
			result = orig_hold(self, *args, **kwargs)
		except _StorageError:
			self.locked_at = 0
			raise
		else:
			self.locked_at = time.time() if result is None or result else 0
			return result

	def release_commit_lock(self, cursor):
		now = time.time()
		try:
			return orig_release(self, cursor)
		finally:
			locked_at = self.locked_at
			self.locked_at = 0
			if locked_at:
				duration = now - locked_at
				if duration > LONG_LOCK_TIME:
					logger.warn("Held global commit locks for %ss", duration)

	cls.hold_commit_lock = hold_commit_lock
	cls.release_commit_lock = release_commit_lock

def _patch():
	locker.StorageError = _StorageError

	# The various lockers may be directly imported in random places
	# already, so we need to patch in place

	_patch_hold_logging(locker.MySQLLocker)
	_patch_hold_logging(locker.OracleLocker)
	_patch_hold_logging(locker.PostgreSQLLocker)
	
_patch()
del _patch

def patch():
	pass
