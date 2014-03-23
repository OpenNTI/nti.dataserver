#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search index manager.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import gevent

from zope import component
from zope import interface

from perfmetrics import metric

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from . import indexagent
from . import search_query
from . import search_results
from . import interfaces as search_interfaces

@interface.implementer(search_interfaces.IIndexManager)
class IndexManager(object):

	indexmanager = None

	@classmethod
	def get_shared_indexmanager(cls):
		return cls.indexmanager

	def __new__(cls, *args, **kwargs):
		if not cls.indexmanager:
			cls.indexmanager = super(IndexManager, cls).__new__(cls)
		return cls.indexmanager

	def __init__(self, parallel_search=True):
		self.parallel_search = parallel_search

	@classmethod
	def get_entity(cls, entity):
		result = Entity.get_entity(str(entity)) \
				 if not nti_interfaces.IEntity.providedBy(entity) else entity
		return result

	@classmethod
	def create_content_searcher(cls, *args, **kwargs):
		factory = component.getUtility(search_interfaces.IContentSearcherFactory)
		result = factory(*args, **kwargs)
		return result

	@metric
	def search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_search_results(query)
		start = time.time()
		if self.parallel_search:
			greenlet = gevent.spawn(self.content_search, query=query, store=results)
			ugd_results = self.user_data_search(query=query, store=results)
			cnt_results = greenlet.get()
		else:
			cnt_results = self.content_search(query=query, store=results)
			ugd_results = self.user_data_search(query=query, store=results)
		results = search_results.merge_search_results(cnt_results, ugd_results)
		logger.debug("Query '%s' returned %s hit(s). Took %.3f(secs)" %
					 (query, len(results), time.time() - start))
		return results

	@metric
	def suggest_and_search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_and_search_results(query)
		cnt_data = self.content_suggest_and_search(query=query, store=results)
		ugd_data = self.user_data_suggest_and_search(query=query, store=results)
		results = search_results.merge_suggest_and_search_results(cnt_data, ugd_data)
		return results

	@metric
	def suggest(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_suggest_results(query)
		cnt_results = self.content_suggest(query=query, store=results)
		ugd_results = self.user_data_suggest(query=query, store=results)
		results = search_results.merge_suggest_results(cnt_results, ugd_results)
		return results

	def get_book_index_manager(self, indexid):
		return self.books.get(indexid, None) if indexid is not None else None

	def register_content(self, ntiid=None, *args, **kwargs):
		if not ntiid:
			return False
		ntiid = ntiid.lower()
		result = component.queryUtility(search_interfaces.IContentSearcher,
									 	name=ntiid) is not None
		if not result:
			searcher = self.create_content_searcher(ntiid=ntiid,
													parallel_search=self.parallel_search,
												  	*args, **kwargs)
			if searcher is not None:
				component.provideUtility(searcher, search_interfaces.IContentSearcher,
									 	 name=ntiid)
				result = True
				logger.info("Content '%s' has been added to index manager", ntiid)
			else:
				logger.error("Content '%s' could not be added to index manager", ntiid)
		return result

	add_book = register_content

	def get_content_searcher(self, query):
		name = query.indexid.lower() if query.indexid else u''
		searcher = component.queryUtility(search_interfaces.IContentSearcher, name=name)
		return searcher

	def content_search(self, query, store=None):
		query = search_interfaces.ISearchQuery(query)
		results = search_results.get_or_create_search_results(query, store)
		searcher = self.get_content_searcher(query)
		if searcher is not None:
			r = searcher.search(query, store=results)
			results = search_results.merge_search_results(results, r)
		return results

	def content_suggest_and_search(self, query, store=None):
		query = search_interfaces.ISearchQuery(query)
		results = search_results.get_or_create_suggest_and_search_results(query, store)
		searcher = self.get_content_searcher(query)
		if searcher is not None:
			rs = searcher.suggest_and_search(query, store=results)
			results = search_results.merge_suggest_and_search_results(results, rs)
		return results

	def content_suggest(self, query, store=None, *args, **kwargs):
		query = search_interfaces.ISearchQuery(query)
		results = search_results.get_or_create_suggest_results(query, store)
		searcher = self.get_content_searcher(query)
		if searcher is not None:
			rs = searcher.suggest(query, store=results)
			results = search_results.merge_suggest_results(results, rs)
		return results

	def user_data_search(self, query, store=None, *args, **kwargs):
		query = search_interfaces.ISearchQuery(query)
		entity = self.get_entity(query.username)
		controller = search_interfaces.IEntityIndexController(entity, None)
		results = controller.search(query, store=store) if controller is not None \
				  else search_results.empty_search_results(query)
		return results

	def user_data_suggest_and_search(self, query, store=None, *args, **kwargs):
		query = search_interfaces.ISearchQuery(query)
		entity = self.get_entity(query.username)
		controller = search_interfaces.IEntityIndexController(entity, None)
		results = controller.suggest_and_search(query, store=store) \
				  if controller is not None \
				  else search_results.empty_suggest_and_search_results(query)
		return results

	def user_data_suggest(self, query, store=None, *args, **kwargs):
		query = search_interfaces.ISearchQuery(query)
		entity = self.get_entity(query.username)
		controller = search_interfaces.IEntityIndexController(entity, None)
		results = controller.suggest(query, store=store) if controller is not None \
				  else search_results.empty_suggest_results(query)
		return results

	def index_user_content(self, target, data, *args, **kwargs):
		if data is not None:
			target = self.get_entity(target)
			controller = search_interfaces.IEntityIndexController(target, None)
			if controller is not None:
				controller.index_content(data)

	def update_user_content(self, target, data, *args, **kwargs):
		if data is not None:
			target = self.get_entity(target)
			controller = search_interfaces.IEntityIndexController(target, None)
			if controller is not None:
				controller.update_content(data)

	def delete_user_content(self, target, data, *args, **kwargs):
		if data is not None:
			target = self.get_entity(target)
			controller = search_interfaces.IEntityIndexController(target, None)
			if controller is not None:
				controller.delete_content(data)

	def unindex(self, target, uid):
		target = self.get_entity(target)
		controller = search_interfaces.IEntityIndexController(target, None)
		return controller.unindex(uid) if controller is not None else None

	def close(self):
		for bm in self.books.itervalues():
			self._close(bm)

	def _close(self, bm):
		close_m = getattr(bm, 'close', None)
		if close_m is not None:
			close_m()

	@classmethod
	def onChange(cls, datasvr, msg, target=None, broadcast=None):
		indexagent.handle_index_event(cls.get_shared_indexmanager(), target, msg,
									  broadcast=broadcast)
