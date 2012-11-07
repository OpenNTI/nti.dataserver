from __future__ import print_function, unicode_literals

import gevent
import random
import collections

from zope import component
from zope import interface
from ZODB import loglevels
from zope.event import notify
from zc import intid as zc_intid

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._redis_indexstore import _RedisStorageService

import logging
logger = logging.getLogger( __name__ )

@interface.implementer(search_interfaces.IRedisStoreService)
class _RepozeRedisStorageService(_RedisStorageService):
	
	wait_time = 0.5
	max_wait_time = 10
	logging_level = loglevels.TRACE
	
	def process_messages(self, msgs):
		users = collections.defaultdict(list)
		
		# organize by entity
		for m in msgs:
			_, _, username =  m  # (op, oid, username)
			users[username].append(m)
			
		# wait some secs to process
		gevent.sleep(random.uniform(3, 4))
		
		for username, msg_list in users.items():
			try:
				self._process_user_messages(username, msg_list)
			except:
				self._push_back_msgs(msg_list, encode=True)		
				logger.exception("Error while processing index message for %s" % username)
			
	def _process_user_messages(self, username, msg_list):
		trxrunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)
		logger.info("Processing %s redis-arriving message(s) for user %s", len(msg_list), username)
		def f():
			entity = Entity.get_entity(username)
			im = search_interfaces.IRepozeEntityIndexManager(entity, None)
			if im is None:
				logger.debug("Cannot adapt to repoze index manager for entity %s" % username)
				return
			
			idx = 0
			retries = 0
			cumulative = 0
			intids = component.getUtility( zc_intid.IIntIds )
			while idx < len(msg_list):
				advance = True
				op, oid, _ = msg_list[idx]
				data = intids.queryObject(int(oid), None)
				if op in ('add', 'update'):
					if data is not None:
						if op == 'add':
							im.index_content(data)
							notify(search_interfaces.IndexEvent(entity, data, search_interfaces.IE_INDEXED))
						else:
							im.update_content(data)
							notify(search_interfaces.IndexEvent(entity, data, search_interfaces.IE_REINDEXED))
					else:
						retries += 1  
						if cumulative <= self.max_wait_time and retries <= 5:
							# sometimes we need to wait to make sure db commit has happened
							# this should go away when we handle index events as zope events
							advance = False
							logger.log(self.logging_level, 'Could not find object %s. Retry %s', oid, retries)
							gevent.sleep(self.wait_time) 
							cumulative += self.wait_time
						else:
							logger.debug('Cannot find object with id %s', oid)
				elif op == 'delete':
					im.unindex_doc(oid)
					notify(search_interfaces.IndexEvent(entity, data or oid, search_interfaces.IE_UNINDEXED))
					
				if advance:
					idx += 1
					retries = 0
					
		trxrunner(f, retries=5, sleep=0.1)
