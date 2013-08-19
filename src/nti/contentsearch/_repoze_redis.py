# -*- coding: utf-8 -*-
"""
Index operations using redis and repoze

$Id: _cloudsearch_store.py 17789 2013-03-31 04:18:10Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.dataserver import users

from . import _discriminators
from ._redis_indexstore import sort_messages
from . import interfaces as search_interfaces
from ._redis_indexstore import _RedisStorageService

@interface.implementer(search_interfaces.IRedisStoreService)
class _RepozeStorageService(_RedisStorageService):

	def index_content(self, docid, username):
		obj = _discriminators.query_object(docid)
		entity = users.Entity.get_entity(username)
		um = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if obj is not None and um is not None:
			return um.index_content(obj)
		return False

	def update_content(self, docid, username):
		obj = _discriminators.query_object(docid)
		entity = users.Entity.get_entity(username)
		um = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if obj is not None and um is not None:
			return um.update_content(obj)
		return False

	def unindex(self, docid, username):
		entity = users.Entity.get_entity(username)
		um = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if um is not None:
			return um.unindex(docid)
		return False

	def process_messages(self, msgs):
		for m in sort_messages(msgs):
			try:
				op, docid, username = m
				if op == 'add':
					self.index_content(docid, username)
				elif op == 'update':
					self.update_content(docid, username)
				elif op == 'delete':
					self.unindex(docid, username)
			except:
				logger.exception("Failed to run index operation %s" % m)
