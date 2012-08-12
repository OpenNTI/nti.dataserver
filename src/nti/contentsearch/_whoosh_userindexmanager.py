from __future__ import print_function, unicode_literals

import time
import random
from hashlib import md5

from zope import interface

from whoosh.store import LockError

from nti.contentsearch import LFUMap
from nti.contentsearch import QueryObject
from nti.contentsearch.interfaces import IUserIndexManager
from nti.contentsearch.interfaces import IUserIndexManagerFactory
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch._whoosh_index import get_indexables
from nti.contentsearch._whoosh_index import get_indexable_object
from nti.contentsearch._search_results import empty_search_result
from nti.contentsearch._search_results import empty_suggest_result
from nti.contentsearch._search_results import merge_search_results
from nti.contentsearch._search_results import merge_suggest_results
from nti.contentsearch._search_results import empty_suggest_and_search_result
from nti.contentsearch._search_results import merge_suggest_and_search_results

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
	
class WhooshUserIndexManager(object):
	interface.implements(IUserIndexManager)

	def __init__(self, username, index_storage, use_md5=True, delay=0.25, maxiters=40):
		self.indices = {}
		self.delay = delay
		self.use_md5 = use_md5
		self.username = username
		self.maxiters = maxiters
		self.index_storage = index_storage

	# -------------------
	
	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'WhooshUserIndexManager(user=%s)' % self.username
	
	def get_username(self):
		return self.username

	@property
	def storage(self):
		return self.index_storage
		
	@property
	def writer_ctor_args(self):
		return self.storage.ctor_args(username=self.username)

	@property
	def writer_commit_args(self):
		return self.storage.commit_args(username=self.username)
		
	# -------------------
	
	def _get_indexname(self, type_name):
		indexname = get_indexname(self.username, type_name, self.use_md5)
		return indexname
	
	def _get_or_create_index(self, type_name):
		type_name = normalize_type_name(type_name)
		indexname = self._get_indexname(type_name)
		index = self.indices.get(indexname, None)
		if not index:
			indexable = get_indexable_object(type_name)
			schema = indexable.get_schema()
			index = self.storage.get_or_create_index(indexname=indexname, schema=schema, username=self.username)
			self.indices[indexname] = index
		return index
	
	def _get_index_writer(self, index):
		writer = None
		counter = 0
		while writer is None:
			try:
				writer = index.writer(**self.writer_ctor_args)
			except LockError, e:
				counter += 1
				if counter <= self.maxiters:
					x = random.uniform(0.1, self.delay)
					time.sleep(x)
				else:
					raise e
		return writer
	
	# -------------------

	class TraxWrapper(object):
		def __init__(self, func):
			self.func = func

		def __call__(self, *args, **kargs):
			return self.func(*args, **kargs)

		def __get__(self, instance, owner):
			def wrapper(*args, **kargs):
				if not hasattr(self, 'storage'):
					self.storage = instance.storage
				return self(instance, *args, **kargs)
			return wrapper
		
	def _adapt_search_on_types(self, search_on=None):
		indexables = get_indexables()
		if search_on:
			search_on = [normalize_type_name(x) for x in search_on if normalize_type_name(x) in indexables]
		return search_on or indexables
	
	def _do_search(self, query, is_quick_search=False, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(query.search_on)
		results = empty_search_result(query.term)
		for type_name in search_on:
			index = self._get_or_create_index(type_name)
			indexable = get_indexable_object(type_name)
			with index.searcher() as searcher:
				if not is_quick_search:
					hits = indexable.search(searcher, query)
				else:
					hits = indexable.ngram_search(searcher, query)
				results = merge_search_results(results, hits)
		return results	
	
	@TraxWrapper
	def search(self, query, *args, **kwargs):
		results = self._do_search(query, False, *args, **kwargs)
		return results

	@TraxWrapper
	def ngram_search(self, query, *args, **kwargs):
		results = self._do_search(query, True, *args, **kwargs)
		return results

	@TraxWrapper
	def suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(query.search_on)
		results = empty_suggest_and_search_result(query.term)
		for type_name in search_on:
			index = self._get_or_create_index(type_name)
			indexable = get_indexable_object(type_name)
			with index.searcher() as searcher:
				rs = indexable.suggest_and_search(searcher, query)
				results = merge_suggest_and_search_results(results, rs)
		return results

	@TraxWrapper
	def suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(query.search_on)
		results = empty_suggest_result(query.term)
		for type_name in search_on:
			index = self._get_or_create_index(type_name)
			indexable = get_indexable_object(type_name)
			with index.searcher() as searcher:
				rs = indexable.suggest(searcher, query)
				results = merge_suggest_results(results, rs)
		return results

	quick_search = ngram_search
	
	# -------------------

	def _get_type_name(self, data=None, **kwargs):
		type_name = kwargs.get('type_name', None) or kwargs.get('typeName', None)
		if not type_name:
			type_name = get_type_name(data) if data else None
		return normalize_type_name(type_name)
	
	@TraxWrapper
	def index_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index:
			indexable = get_indexable_object(type_name)
			writer = self._get_index_writer(index)
			if not indexable.index_content(writer, data, **self.writer_commit_args):
				writer.cancel()
			else:
				return True
		return False

	@TraxWrapper
	def update_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index:
			indexable = get_indexable_object(type_name)
			writer = self._get_index_writer(index)
			if not indexable.update_content(writer, data, **self.writer_commit_args):
				writer.cancel()
			else:
				return True
		return False

	@TraxWrapper
	def delete_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index:
			indexable = get_indexable_object(type_name)
			writer = self._get_index_writer(index)
			if not indexable.delete_content(writer, data, **self.writer_commit_args):
				writer.cancel()
			else:
				return True
		return False

	# -------------------

	def _close_index(self, index):
		index.close()
	
	@TraxWrapper
	def remove_index(self, type_name='Notes'):
		indexname = self._get_indexname(type_name)
		index = self.indices.get(indexname, None)
		if index:
			self.indices.pop(indexname)
			self._close_index(index)

	@TraxWrapper
	def optimize_index(self, type_name='Notes'):
		indexname = self._get_indexname(type_name)
		index = self.indices.get(indexname, None)
		if index:
			index.optimize()

	# -------------------
	
	@TraxWrapper
	def get_stored_indices(self):
		result = get_stored_indices(self.username, self.storage, self.use_md5)
		return result
	
	def has_stored_indices(self):
		names = self.get_stored_indices()
		return True if names else False
	
	# -------------------
	
	@TraxWrapper
	def optimize(self):
		for index in self.indices.itervalues():
			index.optimize()
		
	def close(self):
		for index in self.indices.itervalues():
			self._close_index(index)
		self.indices.clear()
		
	def __del__(self):
		try:
			self.close()
		except:
			pass

class WhooshUserIndexManagerFactory(object):
	interface.implements(IUserIndexManagerFactory)

	def __init__(self, index_storage, max_users=100, use_md5=True, delay=0.25, maxiters=15):
		self.delay = delay
		self.use_md5 = use_md5
		self.maxiters = maxiters
		self.index_storage = index_storage
		self.users = LFUMap(maxsize=max_users, on_removal_callback=self.on_item_removed)

	def __str__( self ):
		return 'users=%s' % len(self.users)

	def __repr__( self ):
		return 'WhooshUserIndexManagerFactory(users=%s)' % len(self.users)
	
	@property
	def storage(self):
		return self.index_storage	
		
	def __call__(self, username, *args, **kwargs):
		uim = self.users.get(username, None)
		create = kwargs.get('create', False)
		if not uim and (create or has_stored_indices(username, self.storage, self.use_md5)):
			uim = WhooshUserIndexManager(username = username,
										 index_storage = self.storage, 
										 use_md5 = self.use_md5,
										 delay = self.delay,
										 maxiters = self.maxiters)
			self.users[username] = uim

		return uim
	
	def on_item_removed(self, key, value):
		try:
			value.close()
		except:
			logger.exception("Error while closing index manager %s" % key)
		
def wuim_factory(index_storage, max_users=100, use_md5=True, delay=0.25, maxiters=15):
	return WhooshUserIndexManagerFactory(index_storage, max_users, use_md5, delay, maxiters)
