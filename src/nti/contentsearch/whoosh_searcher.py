#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Whoosh based content searcher

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import gevent

try:
	from gevent.lock import BoundedSemaphore
except ImportError:
	from threading import BoundedSemaphore

from zope import interface
from zope.proxy import ProxyBase

from whoosh import index

from . import constants
from . import whoosh_query
from . import whoosh_index
from . import search_results
from . import whoosh_storage
from . import interfaces as search_interfaces

class _BoundingProxy(ProxyBase):

	_max_searchers = 64  # Max number of searchers.
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

	CSM = whoosh_query.CosineScorerModel

	def __init__(self, searchable, indexname, index, classname):
		self.index = index
		self.indexname = indexname
		self.classname = classname
		self.searchable = searchable

	def __str__(self):
		return self.indexname

	def __repr__(self):
		return '%s(indexname=%s)' % (self.__class__.__name__, self.indexname)

	def search(self, query, *args, **kwargs):
		query = search_interfaces.ISearchQuery(query)
		with _BoundingProxy(self.index.searcher(weighting=self.CSM)) as s:
			results = self.searchable.search(s, query, *args, **kwargs)
		return results

	def suggest_and_search(self, query, *args, **kwargs):
		query = search_interfaces.ISearchQuery(query)
		with _BoundingProxy(self.index.searcher(weighting=self.CSM)) as s:
			results = self.searchable.suggest_and_search(s, query, *args, **kwargs)
		return results

	def suggest(self, query, *args, **kwargs):
		query = search_interfaces.ISearchQuery(query)
		with _BoundingProxy(self.index.searcher(weighting=self.CSM)) as s:
			results = self.searchable.suggest(s, query, *args, **kwargs)
		return results

	def close(self):
		self.index.close()

INDEX_FACTORIES = \
(
	(constants.book_prefix, whoosh_index.Book, constants.content_),
	(constants.nticard_prefix, whoosh_index.NTICard, constants.nticard_),
	(constants.vtrans_prefix, whoosh_index.VideoTranscript, constants.videotranscript_)
)

@interface.implementer(search_interfaces.IWhooshContentSearcher)
class WhooshContentSearcher(object):

	def __init__(self, baseindexname, storage, ntiid=None,
				 parallel_search=False, *args, **kwargs):
		self._searchables = {}
		self.storage = storage
		self.ntiid = ntiid if ntiid else baseindexname
		for prefix, factory, classsname in INDEX_FACTORIES:
			indexname = prefix + baseindexname
			if not storage.index_exists(indexname):
				continue
			index = storage.get_index(indexname)
			self._searchables[indexname] = \
						_Searchable(factory(), indexname, index, classsname)
		self.parallel_search = parallel_search and len(self._searchables) > 1

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

	def is_valid_content_query(self, s, query):
		result = not query.is_empty
		if result:
			result = not query.searchOn or s.classname in query.searchOn
		return result

	def _execute_search(self, searcher, method, query, store):
		if self.is_valid_content_query(searcher, query):
			method = getattr(searcher, method)
			return method(query, store=store)
		return None

	def search(self, query, store=None, *args, **kwargs):
		greenlets = []
		query = search_interfaces.ISearchQuery(query)
		store = search_results.get_or_create_search_results(query, store)
		for searcher in self._searchables.values():
			if self.parallel_search:
				greenlet = gevent.spawn(self._execute_search, searcher=searcher,
										method="search", query=query, store=store)
				greenlets.append(greenlet)
			else:
				rs = self._execute_search(searcher=searcher, method="search",
										  query=query, store=store)
				store = search_results.merge_search_results(store, rs)
		if greenlets:
			gevent.joinall(greenlets)
			for greenlet in greenlets:
				store = search_results.merge_search_results(store, greenlet.get())
		return store

	def suggest_and_search(self, query, store=None, *args, **kwargs):
		query = search_interfaces.ISearchQuery(query)
		store = search_results.get_or_create_suggest_and_search_results(query, store)
		for s in self._searchables.values():
			if self.is_valid_content_query(s, query):
				rs = s.suggest_and_search(query, store=store)
				store = search_results.merge_suggest_and_search_results(store, rs)
		return store

	def suggest(self, query, store=None, *args, **kwargs):
		query = search_interfaces.ISearchQuery(query)
		store = search_results.get_or_create_suggest_results(query, store)
		for s in self._searchables.values():
			if self.is_valid_content_query(s, query):
				rs = s.suggest(query, store=store)
				store = search_results.merge_suggest_results(store, rs)
		return store

	def close(self):
		for s in self._searchables.values():
			s.close()

@interface.implementer(search_interfaces.IWhooshContentSearcherFactory)
class _ContentSearcherFactory(object):

	def __call__(self, indexname=None, ntiid=None, indexdir=None, *args, **kwargs):
		if indexname and indexdir and os.path.exists(indexdir):
			storage = whoosh_storage.DirectoryStorage(indexdir)
			searcher = WhooshContentSearcher(indexname, storage, ntiid, *args, **kwargs)
			return searcher if len(searcher) > 0 else None
		return None
