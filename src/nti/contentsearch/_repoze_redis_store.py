from __future__ import print_function, unicode_literals

import gevent
import random
import collections

from transaction.interfaces import TransientError

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
	
	logging_level = loglevels.BLATHER
	
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
			
	def _process_message(self, msg):
		trxrunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)
		def f():
			op, oid, username = msg
			entity = Entity.get_entity(username)
			im = search_interfaces.IRepozeEntityIndexManager(entity, None)
			if im is None:
				logger.log(self.logging_level, "Cannot adapt to repoze index manager for entity %s", username)
				return	
			intids = component.getUtility( zc_intid.IIntIds )
			
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
					s = 'Could not find object %s' % oid
					raise TransientError(s)
			elif op == 'delete':
				im.unindex_doc(oid)
				notify(search_interfaces.IndexEvent(entity, data or oid, search_interfaces.IE_UNINDEXED))
		try:	
			trxrunner(f, retries=5, sleep=0.1)
		except TransientError:
			pass
			
	def _process_user_messages(self, username, msg_list):
		for m in msg_list:
			self._process_message(m)
		
