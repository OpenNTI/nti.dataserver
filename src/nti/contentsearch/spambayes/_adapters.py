from __future__ import print_function, unicode_literals

import six
import time
import struct

import BTrees

import zope.intid
from zope import component
from zope import interface
from zope.annotation import factory as an_factory

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as cts_interfaces
from nti.contentsearch.spambayes import interfaces as sps_interfaces
from nti.contentsearch.spambayes.storage import PersistentClassifier

@interface.implementer(sps_interfaces.ISpamClassifier)
@component.adapter(nti_interfaces.IEntity)
class _EntitySpamClassifier(PersistentClassifier):
	pass
	
def _EntitySpamClassifierFactory(user):
	return an_factory(_EntitySpamClassifier)(user)

@interface.implementer(sps_interfaces.ISpamManager)
@component.adapter(nti_interfaces.IEntity)
class _EnitySpamManager(_EntitySpamClassifier):
	
	def __init__(self):
		super(_EnitySpamManager, self).__init__()
		self._marked = BTrees.family64.II.BTree()
	
	def _time_to_64bit_int(self, value ):
		return struct.unpack( b'!Q', struct.pack( b'!d', value ) )[0]

	def _get_uid(self, context):
		if context is not None:
			try:
				_ds_intid = component.getUtility( zope.intid.IIntIds )
				return _ds_intid.queryId(context)
			except:
				pass
		return None
	
	def _get_context(self, uid):
		if uid is not None:
			try:
				_ds_intid = component.getUtility( zope.intid.IIntIds )
				return _ds_intid.queryObject(uid)
			except:
				pass
		return None

	def _get_content(self, obj):
		if isinstance(obj, six.string_types):
			result = obj
		else:
			adapted = component.queryAdapter(obj, cts_interfaces.IContentResolver)
			result = adapted.get_content() if adapted is not None else None
		return result
			
	def is_marked(self, obj):
		uid = obj if isinstance(obj, int) else self._get_uid(obj)
		return uid is not None and uid in self._marked
	
	is_spam = is_marked
	
	def _mark_object(self, obj, mtime=None):
		uid = self._get_uid(obj)
		if uid is not None:
			mtime = mtime or time.time()
			self._marked[uid] = self._time_to_64bit_int(mtime)
			return True
		return False
		
	def _unmark_object(self, obj, mtime=None):
		uid = obj if isinstance(obj, int) else self._get_uid(obj)
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
	
def _EntitySpamManagerFactory(user):
	return an_factory(_EnitySpamManager)(user)

