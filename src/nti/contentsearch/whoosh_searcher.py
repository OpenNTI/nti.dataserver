#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh based content searcher

.. $Id$
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

from zope.container.contained import Contained

from zope.proxy import ProxyBase

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from nti.property.property import CachedProperty

from .constants import content_
from .constants import nticard_
from .constants import book_prefix
from .constants import atrans_prefix
from .constants import vtrans_prefix
from .constants import nticard_prefix
from .constants import audiotranscript_
from .constants import videotranscript_

from .interfaces import ISearchQuery
from .interfaces import IWhooshContentSearcher
from .interfaces import IWhooshContentSearcherFactory

from .search_utils import gevent_spawn

from .search_results import merge_search_results
from .search_results import merge_suggest_results
from .search_results import get_or_create_search_results
from .search_results import get_or_create_suggest_results

from .whoosh_query import CosineScorerModel

from .whoosh_storage import DirectoryStorage

from .whoosh_index import Book as WhooshBook
from .whoosh_index import NTICard as WhooshNTICard
from .whoosh_index import AudioTranscript as WhooshAudioTranscript
from .whoosh_index import VideoTranscript as WhooshVideoTranscript

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

	CSM = CosineScorerModel

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
		query = ISearchQuery(query)
		with _BoundingProxy(self.index.searcher(weighting=self.CSM)) as s:
			results = self.searchable.search(s, query, *args, **kwargs)
		return results

	def suggest_and_search(self, query, *args, **kwargs):
		query = ISearchQuery(query)
		with _BoundingProxy(self.index.searcher(weighting=self.CSM)) as s:
			results = self.searchable.suggest_and_search(s, query, *args, **kwargs)
		return results

	def suggest(self, query, *args, **kwargs):
		query = ISearchQuery(query)
		with _BoundingProxy(self.index.searcher(weighting=self.CSM)) as s:
			results = self.searchable.suggest(s, query, *args, **kwargs)
		return results

	def close(self):
		self.index.close()

INDEX_FACTORIES = (
	(book_prefix, 	 WhooshBook, content_),
	(nticard_prefix, WhooshNTICard, nticard_),
	(atrans_prefix,  WhooshAudioTranscript, audiotranscript_),
	(vtrans_prefix,  WhooshVideoTranscript, videotranscript_)
)

@interface.implementer(IWhooshContentSearcher)
class WhooshContentSearcher(Contained,
							PersistentCreatedAndModifiedTimeObject):

	_baseindexname = None
	_parallel_search = False

	def __init__(self, baseindexname, storage, ntiid=None,
				 parallel_search=False):
		PersistentCreatedAndModifiedTimeObject.__init__(self)
		self.storage = storage
		self._baseindexname = baseindexname
		self._parallel_search = parallel_search
		self.ntiid = ntiid if ntiid else baseindexname

	@CachedProperty
	def _searchables(self):
		result = dict()
		baseindexname = self._baseindexname
		for prefix, factory, classsname in INDEX_FACTORIES:
			indexname = prefix + baseindexname
			if not self.storage.index_exists(indexname):
				logger.warn("Index %s does not exists in storage %r",
							indexname, self.storage)
				continue
			index = self.storage.get_index(indexname)
			result[indexname] = _Searchable(factory(), indexname, index, classsname)
		if not result:
			logger.error("No searchables were found for Index %s in storage %s",
						 baseindexname, self.storage)
		else:
			logger.info("%s searchables were found for Index %s in storage %s",
						len(result), baseindexname, self.storage)
		return result

	@property
	def parallel_search(self):
		return self._parallel_search and len(self._v_searchables) > 1

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

	def __nonzero__(self):
		return True

	def __bool__(self):
		return True

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
		query = ISearchQuery(query)
		store = get_or_create_search_results(query, store)
		for searcher in self._searchables.values():
			if self.parallel_search:
				greenlet = gevent_spawn(func=self._execute_search,
										searcher=searcher,
										method="search",
										query=query,
										store=store)
				greenlets.append(greenlet)
			else:
				rs = self._execute_search(searcher=searcher, method="search",
										  query=query, store=store)
				store = merge_search_results(store, rs)
		if greenlets:
			gevent.joinall(greenlets)
			for greenlet in greenlets:
				store = merge_search_results(store, greenlet.get())
		return store

	def suggest(self, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		store = get_or_create_suggest_results(query, store)
		for s in self._searchables.values():
			if self.is_valid_content_query(s, query):
				rs = s.suggest(query, store=store)
				store = merge_suggest_results(store, rs)
		return store

	def close(self):
		for s in self._searchables.values():
			s.close()

@interface.provider(IWhooshContentSearcherFactory)
def _ContentSearcherFactory(indexname=None, ntiid=None, indexdir=None):
	if indexname and indexdir and os.path.exists(indexdir):
		storage = DirectoryStorage(indexdir)
		searcher = WhooshContentSearcher(indexname, storage, ntiid)
		seacher_length = len(searcher)
		result = searcher if seacher_length > 0 else None
		if result is None:
			logger.error("No indexes were registered for %s,%s (%s)",
						 indexname, indexdir, ntiid)
		else:
			logger.info("%s search-indexes were registered for %s,%s (%s)",
						 seacher_length, indexname, indexdir, ntiid)
		return result
	return None
