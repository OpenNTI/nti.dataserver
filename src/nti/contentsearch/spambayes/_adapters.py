# -*- coding: utf-8 -*-
"""
Spambayes object adapters

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
import time
import struct

import BTrees

import zope.intid
from zope import component
from zope import interface
from zope.annotation import factory as an_factory

from nti.dataserver import interfaces as nti_interfaces

from nti.contentfragments import interfaces as frg_interfaces

from .. import interfaces as cts_interfaces

from .storage import PersistentClassifier
from . import interfaces as sps_interfaces

@interface.implementer(sps_interfaces.ISpamClassifier)
@component.adapter(nti_interfaces.IEntity)
class _EntitySpamClassifier(PersistentClassifier):
	pass

_EntitySpamClassifierFactory = an_factory(_EntitySpamClassifier)

@interface.implementer(sps_interfaces.ISpamManager)
@component.adapter(nti_interfaces.IEntity)
class _EnitySpamManager(_EntitySpamClassifier):

	family = BTrees.family64

	def __init__(self):
		super(_EnitySpamManager, self).__init__()
		self._marked = self.family.II.BTree()

	def _time_to_64bit_int(self, value):
		return struct.unpack(b'!Q', struct.pack(b'!d', value))[0]

	def _query_uid(self, context):
		if context is not None:
			_ds_intid = component.getUtility(zope.intid.IIntIds)
			return _ds_intid.queryId(context)
		return None

	def _get_context(self, uid):
		if uid is not None:
			_ds_intid = component.getUtility(zope.intid.IIntIds)
			return _ds_intid.queryObject(uid)
		return None

	def _get_content(self, obj):
		if isinstance(obj, six.string_types):
			result = unicode(obj)
		else:
			adapted = component.queryAdapter(obj, cts_interfaces.IContentResolver)
			result = adapted.get_content() if adapted is not None else None

		if result:
			result = component.getAdapter(result, frg_interfaces.IPlainTextContentFragment, name='text')
		return result

	def is_marked(self, obj):
		uid = obj if isinstance(obj, (int, long)) else self._query_uid(obj)
		return uid is not None and uid in self._marked

	is_spam = is_marked

	def _mark_object(self, obj, mtime=None):
		uid = self._query_uid(obj)
		if uid is not None:
			mtime = mtime or time.time()
			self._marked[uid] = self._time_to_64bit_int(mtime)
			return True
		return False

	def _unmark_object(self, obj, mtime=None):
		uid = obj if isinstance(obj, int) else self._query_uid(obj)
		if self.is_marked(uid):
			del self._marked[uid]
			return True
		return False

	def mark_spam(self, obj, mtime=None, train=True):
		if self._mark_object(obj, mtime=mtime) and train:
			content = self._get_content(obj)
			if content:
				self.train(content, True)

	def unmark_spam(self, obj, untrain=True):
		if self._unmark_object(obj) and untrain:
			content = self._get_content(obj)
			if content:
				self.untrain(content, True)

	def mark_ham(self, obj):
		content = self._get_content(obj)
		if content:
			self.train(content, False)

_EntitySpamManagerFactory = an_factory(_EnitySpamManager)
