from __future__ import print_function, unicode_literals

import gevent
import random
import collections

import zope.intid
from zope import component
from zope import interface
from ZODB import loglevels
from zope.event import notify

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._redis_indexstore import _RedisStorageService

import logging
logger = logging.getLogger( __name__ )

@interface.implementer(search_interfaces.IRedisStoreService)
class _RepozeRedisStorageService(_RedisStorageService):
	
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
		def f():
			entity = Entity.get_entity(username)
			im = search_interfaces.IRepozeEntityIndexManager(entity, None)
			if im is None:
				logger.debug("Cannot adapt to repoze index manager for entity %s" % username)
				return
			
			_ds_intid = component.getUtility( zope.intid.IIntIds )
			
			idx = 0
			retries = 0
			while idx < len(msg_list):
				op, oid, _ = msg_list[idx]
				oid = int(oid)
				data = _ds_intid.queryObject(oid, None)
				advance = True
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
						if retries <= 5:
							# sometimes we need to wait to make sure db commit has happened
							# this should go away when we handle index events as zope events
							advance = False
							logger.log(self.logging_level, 'Could not find object %s. Retry %s', oid, retries)
							gevent.sleep(0.5) 
						else:
							logger.log(self.logging_level, 'Cannot find object with id %s', oid)
				elif op == 'delete':
					im.unindex_doc(oid)
					notify(search_interfaces.IndexEvent(entity, data or oid, search_interfaces.IE_UNINDEXED))
					
				if advance:
					idx += 1
					retries = 0
					
		trxrunner(f, retries=5, sleep=0.1)
