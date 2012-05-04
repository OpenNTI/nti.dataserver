import sys

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.exfm.cloudsearch import get_search_service
from nti.contentsearch.exfm.cloudsearch import get_document_service

from nti.contentsearch import interfaces
from nti.contentsearch import QueryObject
from nti.contentsearch import SearchCallWrapper
from nti.contentsearch.interfaces import ICloudSearchStore
#from nti.contentsearch.interfaces import IUserIndexManagerFactory
from nti.contentsearch.common import is_all_query
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch.common import indexable_type_names
from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch._cloudsearch_query import parse_query
from nti.contentsearch._cloudsearch_index import get_cloud_oid
from nti.contentsearch._cloudsearch_index import to_cloud_object
from nti.contentsearch._cloudsearch_index import to_external_dict
from nti.contentsearch._cloudsearch_index import search_stored_fields

from nti.contentsearch.common import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT, LAST_MODIFIED, ITEMS,
									  NTIID, HIT_COUNT)

from nti.contentsearch.common import (username_, ngrams_,  content_, oid_, type_)

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

class CloudSearchUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username, ntisearch=None):
		self.username = username
		self.domain = ntisearch or component.getUtility(ICloudSearchStore).get_domain('ntisearch')

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
		
	def _get_errors(self, result, n=5):
		errors = result.errors[:n]
		return '\n'.join(errors)
	
	def index_content(self, data, type_name=None, **kwargs):
		if not data: return None
		
		service = self._get_document_service()
		type_name = normalize_type_name(type_name or get_type_name(data))
		oid, external = to_cloud_object(data, self.username, type_name)
		
		# set 1 as version 
		service.add(oid, 1, external) 
		result = service.commit()
		if result.errors:
			s = self._get_errors(result)
			raise Exception(s)
		return result
	
	# we are not versioning so update is add
	update_content = index_content

	def delete_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		service = self._get_document_service()
		oid = get_cloud_oid(data)
		service.delete(oid, 1) 
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
			oid = get_cloud_oid(oid)
			service.delete(oid, 1) 
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
		results = service.search(bq=bq, return_fields=(oid_,), size=size, start=0)
		for r in results:
			yield r['data'][oid_]
			
	# ---------------------- 
		
	def has_stored_indices(self):
		gen = self.get_aws_oids(size=1)
		objects = list(gen)
		return True if len(objects) else False
		
	def get_stored_indices(self):
		# asume all types are stored
		return list(indexable_type_names)
	
