# -*- coding: utf-8 -*-
"""
Index operations using redis and repoze

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

import functools

from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids.ntiids import find_object_with_ntiid

from . import discriminators
from . import _redis_indexstore
from . import interfaces as search_interfaces

@interface.implementer(search_interfaces.IRedisStoreService)
class _RepozeStorageService(_redis_indexstore._RedisStorageService):

	def index_content(self, docid, ntiid):
		obj = discriminators.query_object(int(docid))
		entity = find_object_with_ntiid(ntiid)
		um = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if obj is not None and um is not None:
			return um.index_content(obj)
		return False

	def update_content(self, docid, ntiid):
		obj = discriminators.query_object(int(docid))
		entity = find_object_with_ntiid(ntiid)
		um = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if obj is not None and um is not None:
			return um.update_content(obj)
		return False

	def unindex(self, docid, ntiid):
		entity = find_object_with_ntiid(ntiid)
		um = search_interfaces.IRepozeEntityIndexManager(entity, None)
		if um is not None:
			return um.unindex(int(docid))
		return False

	_op_delete = unindex
	_op_add = index_content
	_op_update = update_content

	def process_messages(self, msgs):
		run = component.queryUtility(nti_interfaces.IDataserverTransactionRunner)
		for m in _redis_indexstore.sort_messages(msgs):
			__traceback_info__ = m
			try:
				op, docid, username = m
				func = getattr( self, '_op_' + op )
				func = functools.partial( func, docid, username )
				run(func, retries=10, sleep=0.1, job_name=repr(m))
			except:
				logger.exception("Failed to run index operation %s", repr(m))
