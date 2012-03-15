import time
import random
from hashlib import md5

from zope import interface

from whoosh.store import LockError

from nti.contentsearch.interfaces import IUserIndexManager
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch.common import merge_search_results
from nti.contentsearch.common import merge_suggest_results
from nti.contentsearch.common import empty_suggest_and_search_result
from nti.contentsearch.common import merge_suggest_and_search_results
from nti.contentsearch._whoosh_index import get_indexables
from nti.contentsearch._whoosh_index import get_indexable_object

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

class WhooshUserIndexManager(object):
	interface.implements(IUserIndexManager)

	def __init__(self, username, index_storage, use_md5=True, delay=0.25, maxiters=15):
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
	
	def _normalize_name(self, x):
		return x[0:-1].lower() if x.endswith('s') else x.lower()
	
	def _get_indexname(self, type_name):
		type_name = self._normalize_name(type_name)
		if self.use_md5:
			m = md5()
			m.update(self.username)
			m.update(type_name)
			indexname = str(m.hexdigest())
		else:
			indexname = "%s_%s" % (self.username, type_name)
		return indexname
	
	def _get_or_create_index(self, type_name):
		type_name = self._normalize_name(type_name)
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

	def _adapt_search_on_types(self, search_on=None):
		indexables = get_indexables()
		if search_on:
			lm = lambda x: x[0:-1].lower() if x.endswith('s') else x.lower()
			search_on = [lm(x) for x in search_on if lm(x) in indexables]
		return search_on or indexables
	
	def _do_search(self, query, limit=None, search_on=None, is_quick_search=False, **kwargs):
		search_on = self._adapt_search_on_types(search_on)
		results = empty_search_result(query)
		with self.storage.dbTrans():
			for type_name in search_on:
				index = self._get_or_create_index(type_name)
				indexable = get_indexable_object(type_name)
				with index.searcher() as searcher:
					if not is_quick_search:
						hits = indexable.search(searcher, query, limit=limit, **kwargs)
					else:
						hits = indexable.quick_search(searcher, query, limit=limit, **kwargs)
					results = merge_search_results(results, hits)
			
		return results	
	
	def search(self, query, limit=None, search_on=None, *args, **kwargs):
		results = self._do_search(query, limit, search_on, False, search_on, **kwargs)
		return results

	def quick_search(self, query, limit=None, search_on=None, *args, **kwargs):
		results = self._do_search(query, limit, search_on, True, search_on, **kwargs)
		return results

	def suggest_and_search(self, query, limit=None, search_on=None, *args, **kwargs):
		results = empty_suggest_and_search_result(query)
		search_on = self._adapt_search_on_types(search_on)
		with self.storage.dbTrans():
			for type_name in search_on:
				index = self._get_or_create_index(type_name)
				indexable = get_indexable_object(type_name)
				with index.searcher() as searcher:
					rs = indexable.suggest_and_search(searcher=searcher, query=query, limit=limit)
					results = merge_suggest_and_search_results(results, rs)
		return results

	def suggest(self, term, limit=None, prefix=None, search_on=None, *args, **kwargs):
		results = empty_suggest_result(term)
		maxdist = kwargs.get('maxdist', None)
		search_on = self._adapt_search_on_types(search_on)
		with self.storage.dbTrans():
			for type_name in search_on:
				index = self._get_or_create_index(type_name)
				indexable = get_indexable_object(type_name)
				with index.searcher() as searcher:
					rs = indexable.suggest(searcher=searcher, word=term, limit=limit, maxdist=maxdist, prefix=prefix)
					results = merge_suggest_results(results, rs)
		return results

	# -------------------

	def index_content(self, data, type_name='Notes'):
		index = self._get_or_create_index(type_name)
		if index:
			indexable = get_indexable_object(type_name)
			with self.storage.dbTrans():
				writer = self._get_index_writer(index)
				indexable.index_content(writer, data, **self.writer_commit_args)

	def update_content(self, data, type_name='Notes'):
		index = self._get_or_create_index(type_name)
		if index:
			indexable = get_indexable_object(type_name)
			with self.storage.dbTrans():
				writer = self._get_index_writer(index)
				indexable.update_content(writer, data, **self.writer_commit_args)

	def delete_content(self, data, type_name='Notes'):
		index = self._get_or_create_index(type_name)
		if index:
			indexable = get_indexable_object(type_name)
			with self.storage.dbTrans():
				writer = self._get_index_writer(index)
				indexable.delete_content(writer, data, **self.writer_commit_args)

	# -------------------

	def _close_index(self, index):
		index.optimize()
		index.close()

	def remove_index(self, type_name='Notes'):
		indexname = self._get_indexname(type_name)
		index = self.indices.get(indexname, None)
		if index:
			self.indices.pop(indexname)
			self._close_index(index)

	def optimize_index(self, type_name='Notes'):
		indexname = self._get_indexname(type_name)
		index = self.indices.get(indexname, None)
		if index:
			index.optimize()

	##########################
	
	def optimize(self):
		for index in self.indices.itervalues():
			index.optimize()
		
	def close(self):
		for index in self.indices.itervalues():
			self._close_index(index)
		self.indices.clear()

# -----------------------------

def wuim_factory(index_storage, use_md5=True, delay=0.25, maxiters=15):
	def f(username, *args, **kwargs):
		return WhooshUserIndexManager(	username = username,
										index_storage = index_storage, 
										use_md5 = use_md5,
										delay = delay,
										maxiters = maxiters)
	return f
