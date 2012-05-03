import sys

from zope import component
from zope import interface

from nti.dataserver.users import User
from nti.externalization.oids import toExternalOID
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import toExternalObject

from nti.contentsearch.exfm.cloudsearch import get_search_service
from nti.contentsearch.exfm.cloudsearch import get_document_service

from nti.contentsearch import interfaces
from nti.contentsearch import QueryObject
from nti.contentsearch import SearchCallWrapper
#from nti.contentsearch.interfaces import IUserIndexManagerFactory
from nti.contentsearch.common import is_all_query
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import get_last_modified
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch.common import indexable_type_names
from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch._cloudsearch_index import get_object_ngrams
from nti.contentsearch._cloudsearch_index import get_object_content
from nti.contentsearch._search_external import search_external_fields
from nti.contentsearch.utils.nti_reindex_user_content import indexable_objects

from nti.contentsearch.common import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT, CLASS, LAST_MODIFIED, ITEMS,
									  NTIID, HIT_COUNT)
from nti.contentsearch.common import (last_modified_, username_, content_, ngrams_)

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

compute_ngrams = False #TODO: set this as part of a config

_return_fields=[]
for field in search_external_fields:
	field = last_modified_ if field == LAST_MODIFIED else field
	_return_fields.append(field)

# -----------------------------------

class CloudSearchUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username, domain=None):
		self.username = username
		self.domain = domain

	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'CloudSearchUserIndexManager(user=%s)' % self.username

	def get_username(self):
		return self.username
	
	@property
	def dataserver(self):
		return component.getUtility( nti_interfaces.IDataserver )

	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			search_on = [normalize_type_name(x) for x in search_on]
		return search_on or self.store.get_catalog_names(self.username)
	
	def _get_document_service(self):
		return get_document_service(domain=self.domain)
	
	def get_search_service(self):	
		return get_search_service(domain=self.domain)
	
	def _do_search(self, field, qo, search_on, highlight_type):
		results = empty_search_result(qo.term)
		if qo.is_empty: return results
		
		bq = ['(and']
		bq.append("%s:'%s'" % (username_, self.username))
		bq.append("%s:'%s'" % (field, qo.term))
		bq.append('(or')
		for type_name in search_on:
			bq.append("%s:'%s'" % (CLASS, type_name))
		bq.append('))')
		service = self.get_search_service()
		limit = qo.limit or sys.maxint
		start = qo.get('start', 0)
		
		bq = ' '.join(bq)
		objects = service.search(bq=bq, return_fields=_return_fields, size=limit, start=start)
		
		length = len(objects)
		hits = map(get_search_hit, objects, [qo.term]*length, [highlight_type]*length)
		
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
		search_on = self._adapt_search_on_types(qo.search_on)
		highlight_type = None if is_all_query(qo.term) else WORD_HIGHLIGHT
		results = self._do_search(content_, qo, search_on, highlight_type)
		return results
	
	def ngram_search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(qo.search_on)
		highlight_type = None if is_all_query(qo.term) else NGRAM_HIGHLIGHT
		results = self._do_search(ngrams_, qo, search_on, highlight_type)
		return results
	quick_search = ngram_search
	
	# word suggest does not seem to be supported yet in CS
	suggest_and_search = search

	def suggest(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		return empty_suggest_result(qo.term)
		
	# ---------------------- 
	
	def _prepare_index_data(self, obj, type_name):
		oid  = toExternalOID(obj)
		data = toExternalObject(obj)
		
		# make sure the user name is always set
		data[username_] = self.username
		
		# set content
		data[content_] = get_object_content(obj, type_name)
		if compute_ngrams:
			data[ngrams_] = get_object_ngrams(obj, type_name)
			
		# get and update the last modified data
		# cs supports uint ony and we use this number as version also
		lm = int(get_last_modified(data)) 
		data[LAST_MODIFIED] = lm
		
		return oid, data
	
	def index_content(self, data, type_name=None, **kwargs):
		if not data: return None
		
		service = self._get_document_service()
		type_name = normalize_type_name(type_name or get_type_name(data))
		oid, external = self._prepare_index_data(data, type_name)
		
		# set 0 as version 
		service.add(oid, 0, external) 
		result = service.commit()
		if result.errors:
			s = ' '.join(result.errors)
			raise Exception(s)
		return result
	
	# we are not versioning so update is add
	update_content = index_content

	def delete_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		service = self._get_document_service()
		oid = toExternalOID(data)
		service.delete(oid, 0) 
		result = service.commit()
		if result.errors:
			s = ' '.join(result.errors)
			logger.error(s)
			return False
		return True

	def remove_index(self, type_name):
		user = User.get_user(self.username, dataserver=self.dataserver) if self.dataserver else None
		if user:
			service = self._get_document_service()
			for type_name, obj in indexable_objects(user, (type_name,)):
				try:
					oid = toExternalOID(obj)
					service.delete(oid, 0) 
				except:
					pass
			
			result = service.commit()
			if result.errors:
				s = ' '.join(result.errors)
				logger.error(s)
			return result.deletes
		
		return 0
	
	# ---------------------- 
		
	def has_stored_indices(self):
		try:
			bq = "%s:'%s'" % (username_, self.username)
			service = self.get_search_service()
			objects = service.search(bq=bq, return_fields=_return_fields, size=1, start=0)
			return True if len(objects) else False
		except:
			logger.exception("Error while trying to query for all user documents")
		return False
		
	def get_stored_indices(self):
		# asume all types are stored
		return list(indexable_type_names)
	
