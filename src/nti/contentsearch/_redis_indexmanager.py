# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zope.intid
from zope import component

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._indexmanager import IndexManager

class _RedisIndexManager(IndexManager):

	_v_service = None
		
	def __new__(cls, *args, **kwargs):
		if not cls.indexmanager:
			cls.indexmanager = super(_RedisIndexManager, cls).__new__(cls, *args, **kwargs)
		return cls.indexmanager

	def get_uid(self, obj):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		return _ds_intid.getId(obj)
		
	def _get_service(self):
		if self._v_service is None:
			self._v_service = component.getUtility(search_interfaces.IRedisStoreService)
		return self._v_service

	def index_user_content(self, target, data, type_name=None):
		if data is not None and target is not None:
			docid = self.get_uid(data)
			service = self._get_service()
			service.add(docid, username=target.username)
			return True

	def update_user_content(self, target, data, type_name=None):
		if data is not None and target is not None:
			docid = self.get_uid(data)
			service = self._get_service()
			service.update(docid, username=target.username)

	def delete_user_content(self, target, data, type_name=None):
		if data is not None and target is not None:
			docid = self.get_uid(data)
			service = self._get_service()
			service.delete(docid, username=target.username)

