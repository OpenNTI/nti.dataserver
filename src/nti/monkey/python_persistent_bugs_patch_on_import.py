#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Patches some bugs found in the pure-python versions of persistent.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# The current version of invalidate does not correctly
# move forward during invalidation if the value is not
# the first item in the ring
# https://github.com/zopefoundation/persistent/pull/4

from persistent.interfaces import GHOST
from persistent.picklecache import PickleCache

def _invalidate(self, oid):
	value = self.data.get(oid)
	if value is not None and value._p_state != GHOST:
		value._p_invalidate()
		node = self.ring.next
		while node is not self.ring:
			if node.object is value:
				node.prev.next, node.next.prev = node.next, node.prev
				break
			node = node.next # JAM: Addition
	elif oid in self.persistent_classes:
		del self.persistent_classes[oid]

PickleCache._invalidate = _invalidate

# There is a bad interaction with _p_accessed setting
# the MRU time in the picklecache during initial
# serialiaztion: the new object isn't in the picklecache
# yet!
# https://github.com/zopefoundation/persistent/pull/6
from persistent.persistence import Persistent
_orig_p_accessed = Persistent._p_accessed

def _p_accessed(self):
	try:
		_orig_p_accessed(self)
	except KeyError:
		pass

Persistent._p_accessed = _p_accessed

# Persistent in 4.0.6 also has a problem setting the
# state if the dictionary has exactly two keys
# https://github.com/zopefoundation/persistent/pull/5
_orig_setstate = Persistent.__setstate__

def __setstate__(self, state):
	if isinstance(state, dict):
		state = state, ()
	_orig_setstate(self, state)

Persistent.__setstate__ = __setstate__

# In pypy (and possibly in zodbpickle) under python2,
# ZODB 4's ObjectWriter assumes it's working with cPickle
# and sets the wrong attribute to get the
# persistent ids.
# https://github.com/zopefoundation/ZODB/pull/17
import cPickle

from nti.common.property import alias

if 	hasattr(cPickle.Pickler, 'persistent_id') and \
	not hasattr(cPickle.Pickler, 'inst_persistent_id'):
	cPickle.Pickler.inst_persistent_id = alias('persistent_id')

def patch():
	pass

patch()
