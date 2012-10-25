from __future__ import print_function, unicode_literals

import sys
import time
from datetime import datetime

from zope import interface
from zope import component
from zope.annotation import factory as an_factory
from zope.interface.common.mapping import IFullMapping

from persistent.mapping import PersistentMapping

from perfmetrics import metricmethod

from nti.dataserver import interfaces as nti_interfaces

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
from nti.contentsearch._cloudsearch_index import search_stored_fields
from nti.contentsearch._search_indexmanager import _SearchEntityIndexManager
from nti.contentsearch._search_results import empty_suggest_and_search_results

from nti.contentsearch._search_highlights import (WORD_HIGHLIGHT)
from nti.contentsearch.common import (username_, content_, intid_, type_)

import logging
logger = logging.getLogger( __name__ )
	
@component.adapter(nti_interfaces.IEntity)
@interface.implementer(search_interfaces.ICloudSearchEntityIndexManager, IFullMapping)
class _CloudSearchEntityIndexManager(PersistentMapping, _SearchEntityIndexManager):

	_v_service = None
	
	def __init__(self):
		PersistentMapping.__init__(self)

	def _get_cs_service(self):
		if self._v_service is None:
			self._v_service = component.getUtility(search_interfaces.ICloudSearchStoreService)
		return self._v_service

	def _get_search_hit(self, obj):
		cloud_data = obj['data']
		uid = cloud_data.get(intid_, None)
		uid = uid[0] if isinstance(uid, (list, tuple)) else uid
		result = self.get_object(uid) if uid is not None else None
		return (result, 1.0)
		
	def _do_search(self, qo, highlight_type=WORD_HIGHLIGHT, creator_method=None):
		creator_method = creator_method or empty_search_results
		results = creator_method(qo)
		results.highlight_type = highlight_type
		if qo.is_empty: return results
		
		service = self._get_cs_service()

		# perform cloud query
		start = qo.get('start', 0)
		limit = sys.maxint # return all hits
		bq = parse_query(qo, self.username)
		objects = service.search(bq=bq, return_fields=search_stored_fields, size=limit, start=start)
		
		# get ds objects
		for obj in objects:
			hit_score = self._get_search_hit(obj)
			results.add(hit_score)
		return results
	
	@metricmethod
	def search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		highlight_type = None if is_all_query(qo.term) else WORD_HIGHLIGHT
		results = self._do_search(qo, highlight_type)
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
	
	def _check_errors(self, result, n=5, throw=True):
		errors = result.errors[:n] if result is not None else ()
		if errors:
			s = '\n'.join(errors)
			if throw:
				raise Exception(s)
			else:
				logger.error(s)

	def index_content(self, data, type_name=None):
		if not data: return None
		service = self._get_cs_service()
		type_name = normalize_type_name(type_name or get_type_name(data))
		oid, external = to_cloud_object(data, self.username)
		service.add(oid, self.a_version,  external) 
		result = service.commit()
		self._check_errors(result)
		return True
	
	# update is simply and add w/ a different version number
	update_content = index_content

	def delete_content(self, data, type_name=None):
		if not data: return None
		service = self._get_cs_service()
		oid = get_cloud_oid(data)
		service.delete(oid, self.d_version) 
		result = service.commit()
		self._check_errors(result)
		return True

	def remove_index(self, type_name=None):
		counter = 0
		service = self._get_cs_service()
		for oid in self.get_aws_oids(type_name=type_name):
			service.delete(oid, self.d_version)
			counter = counter + 1
		
		if counter:
			result = service.commit()
			self._check_errors(result, throw=False)
			deletes = getattr(result, 'deletes', 0) if result is not None else 0
			return deletes
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
		
		service = self._get_cs_service()
		results = service.search(bq=bq, return_fields=[intid_], size=size, start=0)
		for r in results:
			yield r['id']
			
	# ---------------------- 
		
	def has_stored_indices(self):
		bq = unicode("%s:'%s'" % (username_, self.username))
		service  = self._get_cs_service()
		results = service.search(bq=bq, return_fields=[intid_], size=1, start=0) if service else ()
		return len(results) > 0
		
	def get_stored_indices(self):
		return ()

def _CloudSearchEntityIndexManagerFactory(user):
	result = an_factory(_CloudSearchEntityIndexManager)(user)
	return result
