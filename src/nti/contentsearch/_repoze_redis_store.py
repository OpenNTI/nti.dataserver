from __future__ import print_function, unicode_literals

import collections

import zope.intid
from zope import component
from zope import interface

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._redis_indexstore import _RedisStorageService

import logging
logger = logging.getLogger( __name__ )

@interface.implementer(search_interfaces.IRepozeRedisStoreService)
class _RepozeRedisStorageService(_RedisStorageService):
	
	def process_messages(self, msgs):
		users = collections.defaultdict(list)
		
		# organize by entity
		for m in msgs:
			_, _, username, _, _ =  m  # (op, oid, username, version, external)
			users[username].append(m)
			
		for username, msg_list in users.items():
			try:
				self._process_user_messages(username, msg_list)
			except:
				self._push_back_msgs(msg_list, encode=True)		
				logger.exception("Error while processing index message for %s" % username)
				
	def _process_user_messages(self, username, msgs):
		trxrunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)
		def f():
			entity = Entity.get_entity(username)
			im = search_interfaces.IRepozeRedisEntityIndexManager(entity, None)
			if im is None:
				logger.debug("Cannot adapt to repoze [redis] index manager for entity %s" % username)
				return
			_ds_intid = component.getUtility( zope.intid.IIntIds )
			for op, oid, _, _, _ in msgs:
				oid = int(oid)
				if op in ('add', 'update'):
					data = _ds_intid.queryObject(oid, None)
					if data is not None:
						if op == 'add':
							im.do_index_content(data)
						else:
							im.do_update_content(data)
					else:
						logger.debug("Cannot find object with id %s" % oid)
				elif op == 'delete':
					im.unindex_doc(oid)
				
						
		trxrunner(f, retries=5, sleep=0.1)
