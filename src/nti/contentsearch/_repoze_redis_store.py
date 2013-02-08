# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import gevent
import random

from zope import component
from zope import interface
from ZODB import loglevels
from zope.event import notify
from zc import intid as zc_intid

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._redis_indexstore import sort_messages
from nti.contentsearch._redis_indexstore import _RedisStorageService
from nti.contentsearch._redis_indexstore import (ADD_OPERATION, UPDATE_OPERATION, DELETE_OPERATION)

logger = __import__('logging').getLogger(__name__)

def optimize(msgs_list):
	prev = None
	for i, current in enumerate(msgs_list):
		# (op, oid, username) check same object, same user
		if prev and prev[1] == current[1] and prev[2] == current[2]:
			if current[0] in (DELETE_OPERATION, UPDATE_OPERATION):
				msgs_list[i-1] = None	
		prev = current
	return msgs_list	
	
@interface.implementer(search_interfaces.IRedisStoreService)
class _RepozeRedisStorageService(_RedisStorageService):
	
	wait_time = 0.5
	max_retries = 5
	
	# control the amount of time we spend waiting
	max_cumm_wait_time = 5
	logging_level = loglevels.TRACE
	
	# for testing
	use_trx_runner = True
	
	def initial_wait(self):
		return random.uniform(2, 4)
	
	def process_messages(self, msgs):
		sorted_list = optimize(sort_messages(msgs))
		# wait some random time to start processing
		gevent.sleep(self.initial_wait())
		try:
			self._process_user_messages(sorted_list)
		except:
			self._push_back_msgs(msgs, encode=True)		
			logger.exception("Error while processing index messages")
			
	def _process_user_messages(self, msg_list):
		
		logger.info("Processing %s redis-arriving message(s)", len(msg_list))
		
		def f():
			idx = 0
			retries = 0
			cumulative = 0
			intids = component.getUtility( zc_intid.IIntIds )
			while idx < len(msg_list):
				advance = True
				msg = msg_list[idx]
				if not msg:
					idx += 1
					continue
				
				op, oid, username = msg
				
				entity = Entity.get_entity(username)
				if entity is not None:
					im = search_interfaces.IRepozeEntityIndexManager(entity)
					data = intids.queryObject(int(oid), None)
					if op in (ADD_OPERATION, UPDATE_OPERATION):
						if data is not None:
							if op == ADD_OPERATION:
								im.index_content(data)
								notify(search_interfaces.IndexEvent(entity, data, search_interfaces.IE_INDEXED))
							else:
								im.update_content(data)
								notify(search_interfaces.IndexEvent(entity, data, search_interfaces.IE_REINDEXED))
						else:
							retries += 1  
							if cumulative <= self.max_cumm_wait_time and retries < self.max_retries:
								# sometimes we need to wait to make sure db commit has happened
								# this should go away when we handle index events as zope events
								logger.log(self.logging_level, 'Could not find object %s. Retry %s', oid, retries)
								advance = False
								gevent.sleep(self.wait_time) 
								cumulative += self.wait_time
							else:
								logger.debug('Cannot find object with id %s', oid)
					elif op == DELETE_OPERATION:
						im.unindex_doc(oid)
						notify(search_interfaces.IndexEvent(entity, data or oid, search_interfaces.IE_UNINDEXED))
					
				if advance:
					idx += 1
					retries = 0
		if self.use_trx_runner:		
			trxrunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)
			trxrunner(f, retries=5, sleep=0.1)
		else:
			f()
