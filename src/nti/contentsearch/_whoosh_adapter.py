from __future__ import print_function, unicode_literals

import time
import random
from hashlib import md5

from gevent.coros import RLock

from zope import interface
from zope import component
from zope.proxy import ProxyBase
from zope.annotation import factory as an_factory
from zope.interface.common.mapping import IFullMapping

from persistent.mapping import PersistentMapping

from whoosh.store import LockError

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import LFUMap
from nti.contentsearch import QueryObject
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import sort_search_types
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch._whoosh_index import get_indexables
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._whoosh_index import get_indexable_object
from nti.contentsearch._search_results import empty_search_results
from nti.contentsearch._search_results import merge_search_results
from nti.contentsearch._search_results import empty_suggest_results
from nti.contentsearch._search_results import merge_suggest_results
from nti.contentsearch._search_results import empty_suggest_and_search_results
from nti.contentsearch._search_results import merge_suggest_and_search_results
from nti.contentsearch._search_indexmanager import _SearchEntityIndexManager

import logging
logger = logging.getLogger( __name__ )
		
def get_indexname(username, type_name, use_md5=True):
	type_name = normalize_type_name(type_name)
	if use_md5:
		m = md5()
		m.update(username)
		m.update(type_name)
		indexname = str(m.hexdigest())
	else:
		indexname = "%s_%s" % (username, type_name)
	return indexname

def get_index_writer(index, writer_ctor_args, maxiters, delay):
	counter = 0
	writer = None
	while writer is None:
		try:
			writer = index.writer(**writer_ctor_args)
		except LockError, e:
			counter += 1
			if counter <= maxiters:
				x = random.uniform(0.1, delay)
				time.sleep(x)
			else:
				raise e
	return writer
	
def get_stored_indices(username, storage, use_md5=True):
	result = []
	for type_name in get_indexables():
		type_name = normalize_type_name(type_name)
		index_name = get_indexname(username, type_name, use_md5)
		if storage.index_exists(index_name, username=username):
			result.append(type_name)
	return result
	
def has_stored_indices(username, storage, use_md5=True):
	names = get_stored_indices(username, storage, use_md5)
	return True if names else False
	
# proxy class to wrap an whoosh index

class _Proxy(ProxyBase):
	def __init__(self, obj):
		super(_Proxy, self).__init__(obj)
		self.rlock = RLock()
	
	def __enter__(self):
		return self.rlock.__enter__()

	def __exit__(self, *args, **kwargs):
		return self.rlock.__exit__(*args, **kwargs)

# lease frequently used map to keep open indices
	
def _safe_index_close(index):
	with index:
		try:
			index.close()
		except:
			pass
		
def _on_index_removed(key, value):
	logger.debug('closing index %s' % key)
	_safe_index_close(value)

whoosh_indices = LFUMap(maxsize=500, on_removal_callback=_on_index_removed)
		
# entity adapter for whoosh indicies

@component.adapter(nti_interfaces.IEntity)
class _WhooshEntityIndexManager(PersistentMapping, _SearchEntityIndexManager):
	interface.implements(search_interfaces.IWhooshEntityIndexManager, IFullMapping)
		
	delay = 0.25
	maxiters = 40
	use_md5 = True
		
	@property
	def username(self):
		return self.__parent__.username
	
	@property
	def storage(self):
		result = component.getUtility(search_interfaces.IWhooshIndexStorage)
		return result
		
	@property
	def writer_ctor_args(self):
		return self.storage.default_ctor_args

	@property
	def writer_commit_args(self):
		return self.storage.default_commit_args
		
	# -------------------
	
	def _register_index(self, type_name, index_name, index):
		index = _Proxy(index)
		self[type_name] = index_name
		whoosh_indices[index_name] = index
		return index
		
	def _get_indexname(self, type_name):
		indexname = get_indexname(self.username, type_name, self.use_md5)
		return indexname
	
	def _get_or_create_index(self, type_name):
		type_name = normalize_type_name(type_name)
		indexname = self._get_indexname(type_name)
		index = whoosh_indices.get(indexname, None)
		if not index:
			indexable = get_indexable_object(type_name)
			schema = indexable.get_schema() if indexable else None
			if schema:
				index = self.storage.get_or_create_index(indexname=indexname,
														 schema=schema,
														 username=self.username)
				index = self._register_index(type_name, indexname, index)
		return index
	
	def _get_index_writer(self, index):
		return get_index_writer(index, self.writer_ctor_args, self.maxiters, self.delay)
	
	# -------------------
		
	def _adapt_searchon_types(self, searchon=None):
		indexables = get_indexables()
		if searchon:
			searchon = [normalize_type_name(x) for x in searchon if normalize_type_name(x) in indexables]
		result = searchon or indexables
		result = sort_search_types(result)
		return result
	
	def _do_search(self, query, is_ngram_search=False, **kwargs):
		query = QueryObject.create(query, **kwargs)
		searchon = self._adapt_searchon_types(query.searchon)
		results = empty_search_results(query)
		for type_name in searchon:
			index = self._get_or_create_index(type_name)
			with index:
				indexable = get_indexable_object(type_name)
				with index.searcher() as searcher:
					if not is_ngram_search:
						rs = indexable.search(searcher, query)
					else:
						rs = indexable.ngram_search(searcher, query)
					results = merge_search_results(results, rs)
		return results	

	def search(self, query, *args, **kwargs):
		results = self._do_search(query, False, **kwargs)
		return results

	def ngram_search(self, query, *args, **kwargs):
		results = self._do_search(query, True, **kwargs)
		return results

	def suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		searchon = self._adapt_searchon_types(query.searchon)
		results = empty_suggest_and_search_results(query)
		for type_name in searchon:
			index = self._get_or_create_index(type_name)
			with index:
				indexable = get_indexable_object(type_name)
				with index.searcher() as searcher:
					rs = indexable.suggest_and_search(searcher, query)
					results = merge_suggest_and_search_results(results, rs)
		return results

	def suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		searchon = self._adapt_searchon_types(query.searchon)
		results = empty_suggest_results(query)
		for type_name in searchon:
			index = self._get_or_create_index(type_name)
			with index:
				indexable = get_indexable_object(type_name)
				with index.searcher() as searcher:
					rs = indexable.suggest(searcher, query)
					results = merge_suggest_results(results, rs)
		return results

	# -------------------

	def _get_type_name(self, data=None, **kwargs):
		type_name = kwargs.get('type_name', None) or kwargs.get('typeName', None)
		if not type_name:
			type_name = get_type_name(data) if data else None
		return normalize_type_name(type_name)
	
	def index_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index is not None:
			with index:
				indexable = get_indexable_object(type_name)
				writer = self._get_index_writer(index)
				if not indexable.index_content(writer, data, **self.writer_commit_args):
					writer.cancel()
				else:
					return True
		return False

	def update_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index is not None:
			with index:
				indexable = get_indexable_object(type_name)
				writer = self._get_index_writer(index)
				if not indexable.update_content(writer, data, **self.writer_commit_args):
					writer.cancel()
				else:
					return True
		return False

	def delete_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index is not None:
			with index:
				indexable = get_indexable_object(type_name)
				writer = self._get_index_writer(index)
				if not indexable.delete_content(writer, data, **self.writer_commit_args):
					writer.cancel()
				else:
					return True
		return False

	def remove_index(self, type_name, *args, **kwargs):
		type_name = normalize_type_name(type_name)
		index = self._get_or_create_index(type_name)
		if index is not None:
			with index:
				self.pop(type_name, None)
				whoosh_indices.pop(type_name, None)
				_safe_index_close(index)
	
	# -------------------
	
	def get_stored_indices(self):
		result =  list(self.keys())#s get_stored_indices(self.username, self.storage, self.use_md5)
		return result
	
	def has_stored_indices(self):
		names = self.get_stored_indices()
		return True if names else False	

def _WhooshEntityIndexManagerFactory(user):
	result = an_factory(_WhooshEntityIndexManager)(user)
	return result
