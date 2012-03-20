import time
import random
from hashlib import md5

from zope import interface

from whoosh.store import LockError

from nti.contentsearch.interfaces import IUserIndexManager
from nti.contentsearch.common import get_type_name
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

def normalize_name(x):
	result = u''
	if x:
		result =x[0:-1].lower() if x.endswith('s') else x.lower()
	return unicode(result)
	
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
		type_name = normalize_name(type_name)
		if self.use_md5:
			m = md5()
			m.update(self.username)
			m.update(type_name)
			indexname = str(m.hexdigest())
		else:
			indexname = "%s_%s" % (self.username, type_name)
		return indexname
	
	def _get_or_create_index(self, type_name):
		type_name = normalize_name(type_name)
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
			search_on = [normalize_name(x) for x in search_on if normalize_name(x) in indexables]
		return search_on or indexables
	
	def _do_search(self, query, limit=None, is_quick_search=False, **kwargs):
		search_on = self._adapt_search_on_types(kwargs.get('search_on', None))
		results = empty_search_result(query)
		with self.storage.dbTrans():
			for type_name in search_on:
				index = self._get_or_create_index(type_name)
				indexable = get_indexable_object(type_name)
				with index.searcher() as searcher:
					if not is_quick_search:
						hits = indexable.search(searcher, query, limit=limit, **kwargs)
					else:
						hits = indexable.ngram_search(searcher, query, limit=limit, **kwargs)
					results = merge_search_results(results, hits)
			
		return results	
	
	def search(self, query, limit=None, *args, **kwargs):
		results = self._do_search(query, limit, False, *args, **kwargs)
		return results

	def ngram_search(self, query, limit=None,*args, **kwargs):
		results = self._do_search(query, limit, True, *args, **kwargs)
		return results

	def suggest_and_search(self, query, limit=None, *args, **kwargs):
		results = empty_suggest_and_search_result(query)
		search_on = self._adapt_search_on_types(kwargs.get('search_on', None))
		with self.storage.dbTrans():
			for type_name in search_on:
				index = self._get_or_create_index(type_name)
				indexable = get_indexable_object(type_name)
				with index.searcher() as searcher:
					rs = indexable.suggest_and_search(searcher=searcher, query=query, limit=limit)
					results = merge_suggest_and_search_results(results, rs)
		return results

	def suggest(self, term, limit=None, prefix=None, *args, **kwargs):
		results = empty_suggest_result(term)
		maxdist = kwargs.get('maxdist', None)
		search_on = self._adapt_search_on_types(kwargs.get('search_on', None))
		with self.storage.dbTrans():
			for type_name in search_on:
				index = self._get_or_create_index(type_name)
				indexable = get_indexable_object(type_name)
				with index.searcher() as searcher:
					rs = indexable.suggest(searcher=searcher, word=term, limit=limit, maxdist=maxdist, prefix=prefix)
					results = merge_suggest_results(results, rs)
		return results

	quick_search = ngram_search
	
	# -------------------

	def _get_type_name(self, data=None, **kwargs):
		type_name = get_type_name(data) if data else None
		if not type_name:
			type_name = kwargs.get('type_name', None) or kwargs.get('typeName', None)
		return normalize_name(type_name)
	
	def index_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index:
			indexable = get_indexable_object(type_name)
			with self.storage.dbTrans():
				writer = self._get_index_writer(index)
				if not indexable.index_content(writer, data, **self.writer_commit_args):
					writer.cancel()
				else:
					return True
		return False

	def update_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index:
			indexable = get_indexable_object(type_name)
			with self.storage.dbTrans():
				writer = self._get_index_writer(index)
				if not indexable.update_content(writer, data, **self.writer_commit_args):
					writer.cancel()
				else:
					return True
		return False

	def delete_content(self, data, *args, **kwargs):
		type_name = self._get_type_name(data, **kwargs)
		index = self._get_or_create_index(type_name)
		if index:
			indexable = get_indexable_object(type_name)
			with self.storage.dbTrans():
				writer = self._get_index_writer(index)
				if not indexable.delete_content(writer, data, **self.writer_commit_args):
					writer.cancel()
				else:
					return True
		return False

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

	# -------------------
	
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

# -----------------------------

def wuim_factory(index_storage=None, use_md5=True, delay=0.25, maxiters=15):
	def f(username, *args, **kwargs):
		_use_md5 = kwargs['use_md5'] if 'use_md5' in kwargs else use_md5
		_storage = index_storage or kwargs.get('index_storage', None) or kwargs.get('storage', None)
		return WhooshUserIndexManager(	username = username,
										index_storage = _storage, 
										use_md5 = _use_md5,
										delay = delay,
										maxiters = maxiters)
	return f
