# -*- coding: utf-8 -*-
"""
Whoosh based book index manager

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os

try:
	from gevent.lock import BoundedSemaphore
except ImportError:
	from threading import BoundedSemaphore

from zope import interface
from zope.proxy import ProxyBase

from perfmetrics import metric

from whoosh import index

from ._whoosh_index import Book
from ._whoosh_index import NTICard
from ._search_query import QueryObject
from . import _search_results as srlts
from ._whoosh_index import VideoTranscript
from . import interfaces as search_interfaces
from ._whoosh_indexstorage import DirectoryStorage
from ._whoosh_query import CosineScorerModel as CSM

class _BoundingProxy(ProxyBase):

	_max_searchers = 64  # Max number of searchers. Set in a config?
	_semaphore = BoundedSemaphore(_max_searchers)

	def __init__(self, obj):
		super(_BoundingProxy, self).__init__(obj)
		self.obj = obj

	def __enter__(self):
		self._semaphore.acquire()
		return self.obj.__enter__()

	def __exit__(self, *args, **kwargs):
		result = None
		try:
			result = self.obj.__exit__(*args, **kwargs)
		finally:
			self._semaphore.release()
		return result

class _Searchable(object):

	def __init__(self, searchable, indexname, index):
		self.index = index
		self.indexname = indexname
		self.searchable = searchable

	def __str__(self):
		return self.indexname

	def __repr__(self):
		return '%s(indexname=%s)' % (self.__class__.__name__, self.indexname)

	@metric
	def search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		with _BoundingProxy(self.index.searcher(weighting=CSM)) as s:
			results = self.searchable.search(s, query)
		return results

	def suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		with _BoundingProxy(self.index.searcher(weighting=CSM)) as s:
			results = self.searchable.suggest_and_search(s, query)
		return results

	def suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		with _BoundingProxy(self.index.searcher(weighting=CSM)) as s:
			results = self.searchable.suggest(s, query)
		return results

	def close(self):
		self.index.close()

@interface.implementer(search_interfaces.IWooshBookContentSearcher)
class WhooshBookContentSearcher(object):

	index_factories = (('%s', Book), ('vtrans_%s', VideoTranscript), ('nticard_%s', NTICard))

	def __init__(self, baseindexname, storage, ntiid=None):
		self._searchables = {}
		self.storage = storage
		self.ntiid = ntiid if ntiid else baseindexname
		for prefix, factory in self.index_factories:
			indexname = prefix % baseindexname
			if storage.index_exists(indexname):
				index = storage.get_index(indexname)
				self._searchables[indexname] = _Searchable(factory(), indexname, index)

	@property
	def indices(self):
		return tuple(self._searchables.keys())

	def get_index(self, indexname):
		s = self._searchables.get(indexname)
		result = s.index if s is not None else None
		return result

	def __str__(self):
		return str(self.indices)

	def __repr__(self):
		return '%s(indices=%s)' % (self.__class__.__name__, self.indices)

	def __len__(self):
		return len(self._searchables)

	@metric
	def search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		results = srlts.empty_search_results(query)
		for s in self._searchables.values():
			rs = s.search(query)
			results = srlts.merge_search_results(results, rs)
		return results

	def suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		results = srlts.empty_suggest_and_search_results(query)
		for s in self._searchables.values():
			rs = s.suggest_and_search(query)
			results = srlts.merge_suggest_and_search_results(results, rs)
		return results

	def suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		results = srlts.empty_suggest_results(query)
		for s in self._searchables.values():
			rs = s.suggest(query)
			results = srlts.merge_suggest_results(results, rs)
		return results

	def close(self):
		for s in self._searchables.values():
			s.close()

def wbm_factory(*args, **kwargs):
	def func(indexname, *fargs, **fkwargs):
		ntiid = fkwargs.get('ntiid', None)
		indexdir = fkwargs.get('indexdir', None)
		if os.path.exists(indexdir):
			storage = DirectoryStorage(indexdir)
			searcher = WhooshBookContentSearcher(indexname, storage, ntiid)
			return searcher if len(searcher) > 0 else None
		else:
			return None
	return func
