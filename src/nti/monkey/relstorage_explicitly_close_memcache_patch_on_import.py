#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RelStorage can use a memcache instance to provide tremendous speed benefits.
Relstorage also implements :class:`.IMVCCStorage`, which means its ``new_instance``
and `release` methods are called frequently. These methods can allocate another memcache
connection, but they never explicitly release it, instead relying on Python's
reference counting to release it. However, if there is a cycle, the connection's
reference count may never go to zero, leaving behind a stale, useless open connection.

This patch causes the `release` method to explicitly disconnect the cache connection.

.. Todo:: This same approach can be used for memcache client pooling.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from relstorage.storage import RelStorage

_RelStorage_release = RelStorage.release

def _release(self):
	try:
		_RelStorage_release(self)
	finally:
		for client in self._cache.clients_local_first:
			disconnect = getattr(client, 'disconnect_all', None)
			if disconnect:
				logger.debug("Explicitly disconnecting memcache %s", client)
				disconnect()


def _patch():
	RelStorage.release = _release

_patch()
del _patch
del _release

def patch():
	pass
