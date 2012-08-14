from __future__ import print_function, unicode_literals

import sys
import time
from datetime import datetime

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.interfaces import IUserIndexManagerFactory

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch import QueryObject
from nti.contentsearch import SearchCallWrapper
from nti.contentsearch.common import is_all_query
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch._search_results import empty_search_result
from nti.contentsearch._search_results import empty_suggest_result
from nti.contentsearch._cloudsearch_query import parse_query
from nti.contentsearch._cloudsearch_index import get_cloud_oid
from nti.contentsearch._cloudsearch_index import to_cloud_object
from nti.contentsearch._cloudsearch_index import to_external_dict
from nti.contentsearch._cloudsearch_store import get_search_service
from nti.contentsearch._cloudsearch_index import search_stored_fields
from nti.contentsearch._cloudsearch_store import get_document_service
from nti.contentsearch._search_highlights import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT)
from nti.contentsearch.common import ( LAST_MODIFIED, ITEMS, NTIID, HIT_COUNT)
from nti.contentsearch.common import (username_, ngrams_, content_, oid_, type_)

import logging
logger = logging.getLogger( __name__ )
		
def has_stored_indices(username):
	store = component.getUtility( search_interfaces.ICloudSearchStore )
	domain = store.get_domain('ntisearch')
	bq = "%s:'%s'" % (username_, username)
	service  = get_search_service(domain=domain) if domain else None
	results = service.search(bq=bq, return_fields=[oid_], size=1, start=0) if service else ()
	return len(results) > 0

class CloudSearchUserIndexManager(object):
	interface.implements(search_interfaces.IEntityIndexManager)

	def __init__(self, username, ntisearch=None):
		self.username = username
		self.domain = ntisearch or component.getUtility(search_interfaces.ICloudSearchStore).get_domain('ntisearch')

	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'CloudSearchUserIndexManager(user=%s)' % self.username

	def get_username(self):
		return self.username
	
	@property
	def dataserver(self):
		return component.getUtility( nti_interfaces.IDataserver )
	
	def _get_document_service(self):
		return get_document_service(domain=self.domain)
	
	def _get_search_service(self):	
		return get_search_service(domain=self.domain)
	
	def _get_search_hit(self, obj, query=None, highlight_type=WORD_HIGHLIGHT):
		data = to_external_dict(obj['data'])  
		return get_search_hit(data, query=query, highlight_type=highlight_type)
		
	def _do_search(self, field, qo, highlight_type):
		results = empty_search_result(qo.term)
		if qo.is_empty: return results
		
		service = self._get_search_service()
		
		start = qo.get('start', 0)
		limit = qo.limit or sys.maxint
		bq = parse_query(qo, self.username, field)
		objects = service.search(bq=bq, return_fields=search_stored_fields, size=limit, start=start)
		
		length = len(objects)
		hits = map(self._get_search_hit, objects, [qo.term]*length, [highlight_type]*length)
		
		# filter if required
		hits = hits[:limit] if limit else hits
		
		# get last modified
		lm = reduce(lambda x,y: max(x, y.get(LAST_MODIFIED,0)), hits, 0)
		
		items = results[ITEMS]
		for hit in hits:
			items[hit[NTIID]] = hit
		
		results[LAST_MODIFIED] = lm
		results[HIT_COUNT] = len(items)
		return results
	
	@SearchCallWrapper
	def search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		highlight_type = None if is_all_query(qo.term) else WORD_HIGHLIGHT
		results = self._do_search(content_, qo, highlight_type)
		return results
	
	def ngram_search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		highlight_type = None if is_all_query(qo.term) else NGRAM_HIGHLIGHT
		results = self._do_search(ngrams_, qo, highlight_type)
		return results
	quick_search = ngram_search
	
	# word suggest does not seem to be supported yet in CS
	suggest_and_search = search

	def suggest(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		return empty_suggest_result(qo.term)
		
	# ---------------------- 
	
	@property
	def version(self):
		return int(time.mktime(datetime.utcnow().timetuple()))
	
	@property
	def a_version(self):
		return self.version - 10
	
	@property
	def d_version(self):
		return self.version + 1
	
	def _get_errors(self, result, n=5):
		errors = result.errors[:n]
		return '\n'.join(errors)

	def index_content(self, data, type_name=None, **kwargs):
		if not data: return None
		service = self._get_document_service()
		type_name = normalize_type_name(type_name or get_type_name(data))
		oid, external = to_cloud_object(data, self.username, type_name)
		service.add(oid, self.a_version,  external) 
		result = service.commit()
		if result.errors:
			s = self._get_errors(result)
			raise Exception(s)
		return result
	
	# update is simply and add w/ a different version number
	update_content = index_content

	def delete_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		service = self._get_document_service()
		oid = get_cloud_oid(data)
		service.delete(oid, self.d_version) 
		result = service.commit()
		if result.errors:
			s = ' '.join(result.errors)
			logger.error(s)
			return False
		return True

	def remove_index(self, type_name=None):
		counter = 0
		service = self._get_document_service()
		for oid in self.get_aws_oids(type_name=type_name):
			service.delete(oid, self.d_version)
			counter = counter + 1
		
		if counter:
			result = service.commit()
			logger.info("%s document(s) unindexed" % result.deletes)
			if result.errors:
				s = self._get_errors(result)
				logger.error(s)
			return result.deletes
		return 0
		
	def get_aws_oids(self, type_name=None, size=sys.maxint):
		"""
		return a generator w/ object id of the objects indexed in aws
		"""
		
		# prepare query
		bq = ['(and']
		bq.append("%s:'%s'" % (username_, self.username))
		if type_name:
			bq.append("%s:'%s'" % (type_, type_name))
		bq.append(')')
		bq = ' '.join(bq)
		
		service = self._get_search_service()
		results = service.search(bq=bq, return_fields=[oid_], size=size, start=0)
		for r in results:
			yield r['id']
			
	# ---------------------- 
		
	def has_stored_indices(self):
		return has_stored_indices(self.username)
		
	def get_stored_indices(self):
		return ()
	
class CloudSearchIndexManagerFactory(object):
	interface.implements(IUserIndexManagerFactory)

	singleton = None

	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(CloudSearchIndexManagerFactory, cls).__new__(cls, *args, **kwargs)
		return cls.singleton
	
	def __call__(self, username, *args, **kwargs):
		create = kwargs.get('create', False)
		if create or has_stored_indices(username):
			uim = CloudSearchUserIndexManager(username)
			return uim
		else:
			return None
	
	def on_item_removed(self, key, value):
		try:
			value.close()
		except:
			logger.exception("Error while closing index manager %s" % key)
			
def csim_factory(*args, **kwargs):
	return CloudSearchIndexManagerFactory()
