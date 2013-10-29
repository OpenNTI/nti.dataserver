# -*- coding: utf-8 -*-
"""
Redis based index mananager.

Index events are sent to redis before they are processed

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from . import _indexmanager
from . import discriminators
from . import interfaces as search_interfaces

class _RedisIndexManager(_indexmanager.IndexManager):

	indexmanager = None

	def __new__(cls, *args, **kwargs):
		if not cls.indexmanager:
			cls.indexmanager = super(_RedisIndexManager, cls).__new__(cls)
		return cls.indexmanager

	@property
	def service(self):
		return component.getUtility(search_interfaces.IRedisStoreService)

	def index_user_content(self, target, data, type_name=None):
		if data is not None and target is not None:
			docid = discriminators.get_uid(data)
			self.service.add(docid, username=target.username)
			return True

	def update_user_content(self, target, data, type_name=None):
		if data is not None and target is not None:
			docid = discriminators.get_uid(data)
			self.service.update(docid, username=target.username)

	def delete_user_content(self, target, data, type_name=None):
		if data is not None and target is not None:
			docid = discriminators.get_uid(data)
			self.service.delete(docid, username=target.username)
