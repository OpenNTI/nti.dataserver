#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Based on Products.BTreeFolder2

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from random import randint

from Acquisition import aq_base

from zope.container.contained import notifyContainerModified

from zope.event import notify

from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent import ObjectRemovedEvent

from BTrees.check import check
from BTrees.Length import Length
from BTrees.OOBTree import OOBTree

from persistent import Persistent

from .ofs.folder import Folder
from .ofs.interfaces import ObjectWillBeAddedEvent
from .ofs.interfaces import ObjectWillBeRemovedEvent

from .lazy import LazyMap

_marker = object()

MAX_UNIQUEID_ATTEMPTS = 1000

class ExhaustedUniqueIdsError(Exception):
	pass

class BTreeFolder2Base(Persistent):
	"""
	Base for BTree-based folders.
	"""

	_tree = None  # OOBTree: { id -> object }
	_count = None  # A BTrees.Length
	_v_nextid = 0  # The integer component of the next generated ID

	title = ''

	_objects = ()

	def __init__(self, uid=None):
		if uid is not None:
			self.id = uid
		self._initBTrees()

	def _initBTrees(self):
		self._tree = OOBTree()
		self._count = Length()

	def _populateFromFolder(self, source):
		"""
		Fill this folder with the contents of another folder.
		"""
		for name in source.objectIds():
			value = source._getOb(name, None)
			if value is not None:
				self._setOb(name, aq_base(value))

	def manage_fixCount(self):
		"""
		Calls self._fixCount() and reports the result as text.
		"""
		old, new = self._fixCount()
		path = '/'.join(self.getPhysicalPath())
		if old == new:
			return "No count mismatch detected in BTreeFolder2 at %s." % path
		else:
			return ("Fixed count mismatch in BTreeFolder2 at %s. "
					"Count was %d; corrected to %d" % (path, old, new))

	def _fixCount(self):
		"""
		Checks if the value of self._count disagrees with
		len(self.objectIds()). If so, corrects self._count. Returns the
		old and new count values. If old==new, no correction was
		performed.
		"""
		old = self._count()
		new = len(self.objectIds())
		if old != new:
			self._count.set(new)
		return old, new

	def manage_cleanup(self):
		"""
		Calls self._cleanup() and reports the result as text.
		"""
		v = self._cleanup()
		path = '/'.join(self.getPhysicalPath())
		if v:
			return "No damage detected in BTreeFolder2 at %s." % path
		else:
			return ("Fixed BTreeFolder2 at %s.  "
					"See the log for more details." % path)

	def _cleanup(self):
		"""
		Cleans up errors in the BTrees.

		Certain ZODB bugs have caused BTrees to become slightly insane.
		Fortunately, there is a way to clean up damaged BTrees that
		always seems to work: make a new BTree containing the items()
		of the old one.

		Returns 1 if no damage was detected, or 0 if damage was
		detected and fixed.
		"""

		path = '/'.join(self.getPhysicalPath())
		try:
			check(self._tree)
			for key in self._tree.keys():
				if key not in self._tree:
					raise AssertionError("Missing value for key: %s" % repr(key))
			return 1
		except AssertionError:
			logger.exception('Detected damage to %s. Fixing now.' % path)
			try:
				self._tree = OOBTree(self._tree)
				keys = set(self._tree.keys())
				new = len(keys)
				if self._count() != new:
					self._count.set(new)
			except:
				logger.exception('Failed to fix %s.' % path)
				raise
			else:
				logger.info('Fixed %s.' % path)
			return 0

	def _getOb(self, uid, default=_marker):
		"""
		Return the named object from the folder.
		"""
		try:
			return self._tree[uid].__of__(self)
		except KeyError:
			if default is _marker:
				raise
			else:
				return default

	def get(self, name, default=None):
		return self._getOb(name, default)

	def __getitem__(self, name):
		return self._getOb(name)

	def __getattr__(self, name):
		try:
			return self._tree[name]
		except KeyError:
			raise AttributeError(name)

	def _setOb(self, uid, obj):
		"""
		Store the named object in the folder.
		"""
		tree = self._tree
		if uid in tree:
			raise KeyError('There is already an item named "%s".' % id)
		tree[uid] = obj
		self._count.change(1)

	def _delOb(self, uid):
		"""
		Remove the named object from the folder.
		"""
		tree = self._tree
		del tree[uid]
		self._count.change(-1)

	def objectCount(self):
		"""
		Returns the number of items in the folder.
		"""
		return self._count()

	def __len__(self):
		return self.objectCount()

	def __nonzero__(self):
		return True

	def has_key(self, uid):
		"""
		Indicates whether the folder has an item by ID.
		"""
		return uid in self._tree
	hasObject = has_key  # BWC

	def objectIds(self, spec=None):
		return self._tree.keys()

	def __contains__(self, name):
		return name in self._tree

	def __iter__(self):
		return iter(self.objectIds())

	def objectValues(self, spec=None):
		# Returns a list of actual subobjects of the current object.
		# If 'spec' is specified, returns only objects whose meta_type
		# match 'spec'.
		return LazyMap(self._getOb, self.objectIds(spec))

	def objectItems(self, spec=None):
		# Returns a list of (id, subobject) tuples of the current object.
		# If 'spec' is specified, returns only objects whose meta_type match
		# 'spec'
		return LazyMap(lambda uid, _getOb=self._getOb: (uid, _getOb(uid)),
					   self.objectIds(spec))

	keys = objectIds
	items = objectItems
	values = objectValues

	def _checkId(self, uid, allow_dup=0):
		if not allow_dup and uid in self:
			raise ValueError('The id "%s" is invalid-- it is already in use.' % uid)

	def _setObject(self, uid, obj, suppress_events=False):
		ob = obj
		v = self._checkId(uid)
		if v is not None:
			uid = v

		# If an object by the given id already exists, remove it.
		if uid in self:
			self._delObject(uid)

		if not suppress_events:
			notify(ObjectWillBeAddedEvent(ob, self, uid))

		self._setOb(uid, ob)
		ob = self._getOb(uid)

		if not suppress_events:
			notify(ObjectAddedEvent(ob, self, uid))
			notifyContainerModified(self)

		return uid

	def __setitem__(self, key, value):
		return self._setObject(key, value)

	def _delObject(self, uid, suppress_events=False):
		ob = self._getOb(uid)

		if not suppress_events:
			notify(ObjectWillBeRemovedEvent(ob, self, uid))

		self._delOb(uid)

		if not suppress_events:
			notify(ObjectRemovedEvent(ob, self, uid))
			notifyContainerModified(self)

	def __delitem__(self, name):
		return self._delObject(uid=name)

	# Utility for generating unique IDs.

	def generateId(self, prefix='item', suffix='', rand_ceiling=999999999):
		"""
		Returns an ID not used yet by this folder.

		The ID is unlikely to collide with other threads and clients.
		The IDs are sequential to optimize access to objects
		that are likely to have some relation.
		"""
		uid = None
		attempt = 0
		tree = self._tree
		n = self._v_nextid

		while 1:
			if n % 4000 != 0 and n <= rand_ceiling:
				uid = '%s%d%s' % (prefix, n, suffix)
				if uid not in tree:
					break
			n = randint(1, rand_ceiling)
			attempt = attempt + 1
			if attempt > MAX_UNIQUEID_ATTEMPTS:
				# Prevent denial of service
				raise ExhaustedUniqueIdsError()
		self._v_nextid = n + 1
		return uid

class BTreeFolder2(BTreeFolder2Base, Folder):
	"""
	BTreeFolder2 based on Folder.
	"""

	def _checkId(self, uid, allow_dup=0):
		Folder._checkId(self, uid, allow_dup)
		BTreeFolder2Base._checkId(self, uid, allow_dup)
