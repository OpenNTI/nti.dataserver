#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Based on Zope2.OFS.Folder and Zope2.OFS.ObjectManager

.. $id: __init__.py 59494 2015-02-14 02:16:29Z carlos.sanchez $
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import six
from cgi import escape

from Acquisition import aq_base
from Acquisition import Implicit

from zope.container.contained import notifyContainerModified

from zope.event import notify

from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent import ObjectRemovedEvent

from .interfaces import ObjectWillBeAddedEvent
from .interfaces import ObjectWillBeRemovedEvent

# Constants: __replaceable__ flags:
UNIQUE = 2
REPLACEABLE = 1
NOT_REPLACEABLE = 0

bad_uid = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# @]').search

def checkValidId(self, uid, allow_dup=0):
	# If allow_dup is false, an error will be raised if an object
	# with the given uid already exists. If allow_dup is true,
	# only check that the uid string contains no illegal chars;
	# check_valid_uid() will be called again later with allow_dup
	# set to false before the object is added.

	if not uid or not isinstance(uid, six.string_types):
		if isinstance(uid, unicode):
			uid = escape(uid)
		raise ValueError('Empty or invalid id specified', uid)

	if bad_uid(uid) is not None:
		raise ValueError(
			'The id "%s" contains characters illegal in URLs.' % escape(uid))

	if uid in ('.', '..'):
		raise ValueError(
				'The id "%s" is invalid because it is not traversable.' % uid)

	if uid.startswith('_'):
		raise ValueError(
				'The id "%s" is invalid because it begins with an underscore.' % uid)

	if uid.startswith('aq_'):
		raise ValueError(
				'The id "%s" is invalid because it begins with "aq_".' % uid)

	if uid.endswith('__'):
		raise ValueError(
				'The id "%s" is invalid because it ends with two underscores.' % uid)

	if not allow_dup:
		obj = getattr(self, uid, None)
		if obj is not None:
			# An object by the given uid exists either in this
			# folder or in the acquisition path.
			flags = getattr(obj, '__replaceable__', NOT_REPLACEABLE)
			if hasattr(aq_base(self), uid):
				# The object is located in this folder.
				if not flags & REPLACEABLE:
					raise ValueError(
							'The id "%s" is invalid - it is already in use.' % uid)
				# else the object is replaceable even if the UNIQUE
				# flag is set.
			elif flags & UNIQUE:
				raise ValueError('The id "%s" is reserved.' % uid)
	if '/' in uid:
		raise ValueError(
			'The id "%s" contains characters illegal in URLs.' % uid)

_marker = object()

class ObjectManager(Implicit):

	_objects = ()

	_checkId = checkValidId

	def _setOb(self, uid, obj):
		setattr(self, uid, obj)

	def _delOb(self, uid):
		delattr(self, uid)

	def _getOb(self, uid, default=_marker):
		if uid[:1] != '_' and hasattr(aq_base(self), uid):
			return getattr(self, uid)
		if default is _marker:
			raise AttributeError(uid)
		return default

	def hasObject(self, uid):
		"""
		Indicate whether the folder has an item by ID.

		This doesn't try to be more intelligent than _getOb, and doesn't
		consult _objects (for performance reasons). The common use case
		is to check that an object does *not* exist.
		"""
		if (uid in ('.', '..')
			or uid.startswith('_')
			or uid.startswith('aq_')
			or uid.endswith('__')):
			return False
		return getattr(aq_base(self), uid, None) is not None

	def _setObject(self, uid, obj, suppress_events=False):
		"""
		Set an object into this container.

		Also sends IObjectWillBeAddedEvent and IObjectAddedEvent.
		"""
		ob = obj  # better name, keep original function signature
		v = self._checkId(uid)
		if v is not None:
			uid = v

		# If an object by the given id already exists, remove it.
		for object_info in self._objects:
			if object_info['id'] == uid:
				self._delObject(uid)
				break

		if not suppress_events:
			notify(ObjectWillBeAddedEvent(ob, self, uid))

		self._objects = self._objects + ({'id': uid},)
		self._setOb(uid, ob)
		ob = self._getOb(uid)

		if not suppress_events:
			notify(ObjectAddedEvent(ob, self, uid))
			notifyContainerModified(self)

		return uid

	def _delObject(self, uid, suppress_events=False):
		"""
		Delete an object from this container.

		Also sends IObjectWillBeRemovedEvent and IObjectRemovedEvent.
		"""
		ob = self._getOb(uid)

		if not suppress_events:
			notify(ObjectWillBeRemovedEvent(ob, self, uid))

		self._objects = tuple([i for i in self._objects
							   if i['id'] != uid])
		self._delOb(uid)

		try:
			ob._v__object_deleted__ = 1
		except:
			pass

		if not suppress_events:
			notify(ObjectRemovedEvent(ob, self, uid))
			notifyContainerModified(self)

	def objectIds(self):
		return [ o['id']  for o in self._objects ]

	def objectValues(self):
		return [ self._getOb(uid) for uid in self.objectIds() ]

	def objectItems(self):
		return [ (id, self._getOb(uid)) for uid in self.objectIds() ]

	def objectMap(self):
		return tuple(d.copy() for d in self._objects)

	def __delitem__(self, name):
		return self.manage_delObjects(ids=[name])

	def __getitem__(self, key):
		if key in self:
			return self._getOb(key, None)
		raise KeyError(key)

	def __setitem__(self, key, value):
		return self._setObject(key, value)

	def __contains__(self, name):
		return name in self.objectIds()

	def __iter__(self):
		return iter(self.objectIds())

	def __len__(self):
		return len(self.objectIds())

	def __nonzero__(self):
		return True

	def get(self, key, default=None):
		if key in self:
			return self._getOb(key, default)
		return default

	def keys(self):
		return self.objectIds()

	def items(self):
		return self.objectItems()

	def values(self):
		return self.objectValues()
