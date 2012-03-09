import logging
logger = logging.getLogger( __name__ )

import time
from hashlib import md5

from whoosh.store import LockError

from contenttypes import empty_search_result
from contenttypes import empty_suggest_result
from contenttypes import merge_search_results
from contenttypes import merge_suggest_results
from contenttypes import empty_suggest_and_search_result
from contenttypes import merge_suggest_and_search_results

from zope import interface
from . import interfaces
from . import IndexTypeMixin, singleton
from contenttypes import content_type_class

class UserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username, index_storage, use_md5=True,delay=0.25):
		self.username = username
		self.indices = {}
		self.delay = delay
		self.use_md5 = use_md5
		self.index_storage = index_storage

	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'UserIndexManager(user=%s, indices=%s, storage=%s)' % (self.username, self.indices, self.index_storage)

	@property
	def storage(self):
		return self.index_storage

	def get_content_type(self,  typeName='Notes', indexname=None):
		indexname = indexname or self.get_content_indexname(typeName)
		return self.indices[indexname].instance if self.indices.has_key(indexname) else None

	def __ctor_args(self):
		return self.storage.ctor_args(username=self.username)

	def get_writer(self, index):
		writer = None
		#TODO: We should put a limit 
		while writer is None:
			try:
				writer = index.writer(**self.__ctor_args())
			except LockError:
				time.sleep(self.delay)
		return writer

	def get_content_writer(self, typeName='Notes', indexname=None):
		indexname = indexname or self.get_content_indexname(typeName)
		return self.get_writer(self.indices[indexname].index) if self.indices.has_key(indexname) else None

	def get_content_searcher(self, typeName='Notes'):
		index = self.get_content_index(typeName, False)
		return index.searcher() if index else None

	@classmethod
	def content_indexname(cls, username, typeName='Notes', use_md5=True):
		content_type = content_type_class(typeName)
		if use_md5:
			m = md5()
			m.update(username)
			m.update(content_type.__name__.lower())
			indexname = str(m.hexdigest())
		else:
			indexname = username + "_" + content_type.__name__.lower()

		return indexname

	def get_content_indexname(self, typeName='Notes'):
		return self.content_indexname(self.username, typeName, self.use_md5)

	def get_content_index(self, typeName='Notes', create=True):
		indexname = self.get_content_indexname(typeName)
		if not self.indices.has_key(indexname):

			if not create: return None

			type_instance = singleton(content_type_class(typeName))
			schema = type_instance.get_schema()
			if not schema: return None

			idx = self.storage.get_or_create_index(indexname=indexname, schema=schema, username=self.username)
			self.indices[indexname] = IndexTypeMixin(type_instance, idx)

			logger.debug("Index '%s' was created for user %s to store %s objects",\
						 indexname, self.username, type_instance.__class__.__name__)

		return self.indices[indexname]

	def register_index(self, typeName='Notes', auto_create=True):
		indexname = self.get_content_indexname(typeName)
		if not self.indices.has_key(indexname):

			type_instance = singleton(content_type_class(typeName))
			if auto_create:
				schema = type_instance.get_schema()
				if not schema: return
				idx = self.storage.get_or_create_index(indexname=indexname, schema=schema, username=self.username)
			else:
				idx = self.storage.get_index(indexname=indexname, username=self.username)

			if idx:
				self.indices[indexname] = IndexTypeMixin(type_instance, idx)
				logger.debug("Index '%s' was registered to user %s to store %s objects",\
						 	 indexname, self.username, type_instance.__class__.__name__)

	##########################

	def _adapt_search_on(self, search_on=None):
		if search_on:
			lm = lambda x: x[0:-1] if x.endswith('s') else x
			search_on = [lm(x) for x in search_on]
		return search_on

	def search(self, query, limit=None, search_on=None):
		results = None
		search_on = self._adapt_search_on(search_on)
		for t in self.indices.itervalues():
			if not search_on or t.type_name in search_on:
				with t.index.searcher() as searcher:
					rs = t.instance.search(searcher=searcher, query=query, limit=limit)
					results = merge_search_results(results, rs)
		return results if results else empty_search_result(query)

	def quick_search(self, query, limit=None, search_on=None):
		results = None
		search_on = self._adapt_search_on(search_on)
		for t in self.indices.itervalues():
			if not search_on or t.type_name in search_on:
				with t.index.searcher() as searcher:
					rs = t.instance.quick_search(searcher=searcher, query=query, limit=limit)
					results = merge_search_results(results, rs)
		return results if results else empty_search_result(query)

	def suggest_and_search(self, query, limit=None, search_on=None):
		results = None
		search_on = self._adapt_search_on(search_on)
		for t in self.indices.itervalues():
			if not search_on or t.type_name in search_on:
				with t.index.searcher() as searcher:
					rs = t.instance.suggest_and_search(searcher=searcher, query=query, limit=limit)
					results = merge_suggest_and_search_results(results, rs)
		return results if results else empty_suggest_and_search_result(query)

	def suggest(self, term, limit=None, prefix=None, search_on=None, **kwargs):
		results = None
		maxdist = kwargs.get('maxdist', None)
		search_on = self._adapt_search_on(search_on)
		for t in self.indices.itervalues():
			if not search_on or t.type_name in search_on:
				with t.index.searcher() as searcher:
					rs = t.instance.suggest(searcher=searcher, word=term, limit=limit, maxdist=maxdist, prefix=prefix)
					results = merge_suggest_results(results, rs)
		return results if results else empty_suggest_result(term)

	def externalize(self, typeName='Notes'):
		t = self.get_content_index(typeName, False)
		if t:
			with t.index.reader() as reader:
				for s in reader.all_stored_fields():
					t.instance.externalize(s)

	##########################

	def index_content(self, externalValue, typeName='Notes'):
		t = self.get_content_index(typeName, True)
		if t:
			writer = self.get_content_writer(indexname=t.indexname)
			t.instance.index_content(writer, externalValue, **self.__commit_args())

	def update_content(self, externalValue, typeName='Notes'):
		t = self.get_content_index(typeName, True)
		if t:
			writer = self.get_content_writer(indexname=t.indexname)
			t.instance.update_content(writer, externalValue, **self.__commit_args())

	def delete_content(self, externalValue, typeName='Notes'):
		t = self.get_content_index(typeName, False)
		if t:
			writer = self.get_content_writer(indexname=t.indexname)
			t.instance.delete_content(writer, externalValue, **self.__commit_args())

	def __commit_args(self):
		return self.storage.commit_args(username=self.username)

	##########################

	def _close_index(self, idx):
		idx.optimize()
		idx.close()

	def remove_index(self, typeName='Notes'):
		t = self.get_content_index(typeName, False)
		if t: self._close_index(t.index)

	def optimize_index(self, typeName='Notes'):
		t = self.get_content_index(typeName, False)
		if t: t.index.optimize()

	##########################
	
	def optimize(self):
		for t in self.indices.itervalues():
			t.index.optimize()
		
	def close(self):
		for t in self.indices.itervalues():
			self._close_index(t.index)
		self.indices.clear()

