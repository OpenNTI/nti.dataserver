from __future__ import print_function, unicode_literals

import sys
import time
from datetime import datetime

from zope import interface
from zope import component
from zope.annotation import factory as an_factory

from persistent import Persistent

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import SearchCallWrapper
from nti.contentsearch.common import is_all_query
from nti.contentsearch.common import get_type_name
from nti.contentsearch._search_query import QueryObject
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch._cloudsearch_query import parse_query
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._cloudsearch_index import get_cloud_oid
from nti.contentsearch._cloudsearch_index import to_cloud_object
from nti.contentsearch._search_results import empty_search_results
from nti.contentsearch._search_results import empty_suggest_results
from nti.contentsearch._cloudsearch_store import get_search_service
from nti.contentsearch._cloudsearch_index import search_stored_fields
from nti.contentsearch._cloudsearch_store import get_document_service
from nti.contentsearch._search_indexmanager import _SearchEntityIndexManager
from nti.contentsearch._search_results import empty_suggest_and_search_results

from nti.contentsearch._search_highlights import (WORD_HIGHLIGHT)
from nti.contentsearch.common import (username_, content_, intid_, type_)

import logging
logger = logging.getLogger( __name__ )
	
@component.adapter(nti_interfaces.IEntity)
@interface.implementer(search_interfaces.ICloudSearchEntityIndexManager)
class _CloudSearchEntityIndexManager(Persistent, _SearchEntityIndexManager):

	@property
	def domain(self):
		cs = component.getUtility(search_interfaces.ICloudSearchStore)
		result = cs.get_search_domain()
		return result
	
	def _get_document_service(self):
		return get_document_service(domain=self.domain)
	
	def _get_search_service(self):	
		return get_search_service(domain=self.domain)
	
	def _get_search_hit(self, obj):
		cloud_data = obj['data']
		uid = cloud_data.get(intid_, None)
		result = self.get_object(int(uid)) if uid else None
		return result
		
	def _do_search(self, field, qo, highlight_type=WORD_HIGHLIGHT, creator_method=None):
		creator_method = creator_method or empty_search_results
		results = creator_method(qo)
		results.highlight_type = highlight_type
		if qo.is_empty: return results
		
		service = self._get_search_service()
		
		# perform cloud query
		start = qo.get('start', 0)
		limit = sys.maxint # return all hits
		bq = parse_query(qo, self.username, field)
		objects = service.search(bq=bq, return_fields=search_stored_fields, size=limit, start=start)
		
		# get ds objects
		results.add(map(self._get_search_hit, objects))
		return results
	
	@SearchCallWrapper
	def search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		highlight_type = None if is_all_query(qo.term) else WORD_HIGHLIGHT
		results = self._do_search(content_, qo, highlight_type)
		return results

	def suggest(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		return empty_suggest_results(qo)
		
	def suggest_and_search(self, query, *args, **kwargs):
		# word suggest does not seem to be supported yet in cloud search
		qo = QueryObject.create(query, **kwargs)
		return self._do_search(content_, qo, creator_method=empty_suggest_and_search_results)
	
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

	def index_content(self, data, type_name=None):
		if not data: return None
		service = self._get_document_service()
		type_name = normalize_type_name(type_name or get_type_name(data))
		oid, external = to_cloud_object(data, self.username, type_name)
		service.add(oid, self.a_version,  external) 
		result = service.commit()
		if result.errors:
			s = self._get_errors(result)
			raise Exception(s)
		return True
	
	# update is simply and add w/ a different version number
	update_content = index_content

	def delete_content(self, data, type_name=None):
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
		return a generator w/ int ids of the objects indexed in aws
		"""
		
		# prepare query
		bq = ['(and']
		bq.append("%s:'%s'" % (username_, self.username))
		if type_name:
			bq.append("%s:'%s'" % (type_, type_name))
		bq.append(')')
		bq = ' '.join(bq)
		
		service = self._get_search_service()
		results = service.search(bq=bq, return_fields=[intid_], size=size, start=0)
		for r in results:
			yield r['id']
			
	# ---------------------- 
		
	def has_stored_indices(self):
		bq = unicode("%s:'%s'" % (username_, self.username))
		service  = self._get_search_service()
		results = service.search(bq=bq, return_fields=[intid_], size=1, start=0) if service else ()
		return len(results) > 0
		
	def get_stored_indices(self):
		return ()

def _CloudSearchEntityIndexManagerFactory(user):
	result = an_factory(_CloudSearchEntityIndexManager)(user)
	return result
