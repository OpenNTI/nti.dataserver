#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from Acquisition import aq_base

from zope.component import adapter

from zope.container.contained import notifyContainerModified

from zope.interface import implementer

from .interfaces import IOrderable
from .interfaces import IOrderableFolder
from .interfaces import IExplicitOrdering

ORDER_ATTR = '_objectordering'

@adapter(IOrderableFolder)
@implementer(IExplicitOrdering)
class PartialOrdering(object):
	"""
	this implementation uses a list ot store order information on a
	regular attribute of the folderish object;  explicit ordering
	is supported """

	def __init__(self, context):
		self.context = context

	@property
	def order(self):
		context = aq_base(self.context)
		if not hasattr(context, ORDER_ATTR):
			setattr(context, ORDER_ATTR, [])
		return getattr(context, ORDER_ATTR)

	def notifyAdded(self, uid):
		assert not uid in self.order
		context = aq_base(self.context)
		obj = context._getOb(uid)
		if IOrderable.providedBy(obj):
			self.order.append(uid)
			self.context._p_changed = True  # the order was changed

	def notifyRemoved(self, uid):
		try:
			self.order.remove(uid)
			self.context._p_changed = True  # the order was changed
		except ValueError:  # removing non-orderable items is okay
			pass

	def idsInOrder(self, onlyOrderables=False):
		ordered = list(self.order)
		if not onlyOrderables:
			ids = aq_base(self.context).objectIds(ordered=False)
			unordered = set(ids).difference(set(ordered))
			ordered += list(unordered)
		return ordered

	def moveObjectsByDelta(self, ids, delta, subset_ids=None, suppress_events=False):
		min_position = 0
		if isinstance(ids, basestring):
			ids = [ids]
		if subset_ids is None:
			subset_ids = self.idsInOrder(onlyOrderables=True)
		elif not isinstance(subset_ids, list):
			subset_ids = list(subset_ids)
		if delta > 0:  # unify moving direction
			ids = reversed(ids)
			subset_ids.reverse()
		counter = 0
		for uid in ids:
			try:
				old_position = subset_ids.index(uid)
			except ValueError:
				continue
			new_position = max(old_position - abs(delta), min_position)
			if new_position == min_position:
				min_position += 1
			if not old_position == new_position:
				subset_ids.remove(uid)
				subset_ids.insert(new_position, uid)
				counter += 1
		if counter > 0:
			if delta > 0:
				subset_ids.reverse()
			idx = 0
			for i, value in enumerate(self.order):
				if value in subset_ids:
					uid = subset_ids[idx]
					try:
						self.order[i] = uid
						idx += 1
					except KeyError:
						raise ValueError('No object with id "%s" exists.' % uid)
			if idx > 0:
				self.context._p_changed = True  # the order was changed
		if not suppress_events:
			notifyContainerModified(self.context)
		return counter

	def moveObjectsUp(self, ids, delta=1, subset_ids=None):
		return self.moveObjectsByDelta(ids, -delta, subset_ids)

	def moveObjectsDown(self, ids, delta=1, subset_ids=None):
		return self.moveObjectsByDelta(ids, delta, subset_ids)

	def moveObjectsToTop(self, ids, subset_ids=None):
		return self.moveObjectsByDelta(ids, -len(self.order), subset_ids)

	def moveObjectsToBottom(self, ids, subset_ids=None):
		return self.moveObjectsByDelta(ids, len(self.order), subset_ids)

	def moveObjectToPosition(self, uid, position, suppress_events=False):
		old_position = self.getObjectPosition(uid)
		if old_position is not None:
			delta = position - old_position
			if delta:
				return self.moveObjectsByDelta(uid, delta, suppress_events=suppress_events)

	def orderObjects(self, key=None, reverse=None):
		if key is None:
			if not reverse:
				return -1
			else:
				# Simply reverse the current ordering.
				self.order.reverse()
		else:
			def keyfn(uid):
				attr = getattr(self.context._getOb(uid), key)
				if callable(attr):
					return attr()
				return attr

			self.order.sort(None, keyfn, bool(reverse))
		self.context._p_changed = True  # the order was changed
		return -1

	def getObjectPosition(self, uid):
		try:
			# using `index` here might not be that efficient for very large
			# lists, but the idea behind this adapter is to use it when the
			# site contains relatively few "orderable" items
			return self.order.index(uid)
		except ValueError:
			# non-orderable objects should return "no position" instead of
			# breaking things when partial ordering support is active...
			if self.context.hasObject(uid):
				return None
			raise ValueError('No object with id "%s" exists.' % uid)
