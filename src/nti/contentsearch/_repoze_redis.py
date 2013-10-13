# -*- coding: utf-8 -*-
"""
Index operations using redis and repoze

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

import functools

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces

from . import _discriminators
from ._redis_indexstore import sort_messages
from . import interfaces as search_interfaces
from ._redis_indexstore import _RedisStorageService

@interface.implementer(search_interfaces.IRedisStoreService)
class _RepozeStorageService(_RedisStorageService):

	def index_content(self, docid, username):
		obj = _discriminators.query_object(int(docid))
		entity = users.Entity.get_entity(username)
		um = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if obj is not None and um is not None:
			return um.index_content(obj)
		return False

	def update_content(self, docid, username):
		obj = _discriminators.query_object(int(docid))
		entity = users.Entity.get_entity(username)
		um = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if obj is not None and um is not None:
			return um.update_content(obj)
		return False

	def unindex(self, docid, username):
		entity = users.Entity.get_entity(username)
		um = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if um is not None:
			return um.unindex(int(docid))
		return False

	_op_add = index_content
	_op_update = update_content
	_op_delete = unindex

	def process_messages(self, msgs):
		run = component.queryUtility(nti_interfaces.IDataserverTransactionRunner)
		for m in sort_messages(msgs):
			__traceback_info__ = m
			try:
				op, docid, username = m
				func = getattr( self, '_op_' + op )
				func = functools.partial( func, docid, username )

				run( func, retries=None )
			except:
				logger.exception("Failed to run index operation %s", repr(m))
