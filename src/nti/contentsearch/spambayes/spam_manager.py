from __future__ import print_function, unicode_literals

import time

import zope.intid
from zope import component

from persistent import Persistent
from BTrees.LFBTree import LFBTree
from BTrees.LOBTree import LOBTree
from BTrees.LLBTree import LLTreeSet

from nti.dataserver import interfaces as nti_interfaces
	
class SpamManager(Persistent):

	def __init__(self):
		self._id2date = LFBTree()
		self._date2ids = LOBTree()
		
	def mark_spam(self, context, mtime=None):
		m_time = mtime or time.time()
		l_time = long(m_time)
		if nti_interfaces.IModeledContent.providedBy(context):
			uid = self.get_uid(context)
			if not uid in self._id2date:
				self._id2date[uid] = m_time
				if not l_time in self._date2ids:
					self._date2ids[l_time] = LLTreeSet()
				self._date2ids[l_time].add(uid)
				return True
		return False
				
	def unmark_spam(self, context, mtime=None):
		m_time = mtime or time.time()
		l_time = long(m_time)
		if nti_interfaces.IModeledContent.providedBy(context):
			uid = self.get_uid(context)
			if uid in self._id2date:
				self._id2date.pop(uid, None)
				self._date2ids[l_time].remove(uid)
				return True
		return False

	def get_uid(self, context):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		return _ds_intid.getId(context)
	
	def get_context(self, uid):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		return _ds_intid.getObject(uid)
	


