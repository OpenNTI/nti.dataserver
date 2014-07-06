#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Index manager

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from zope import interface

from perfmetrics import metric

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from . import search_query
from . import search_utils
from . import search_results

from .interfaces import IIndexManager
from .interfaces import IContentSearcherFactory
from .interfaces import IContentSearcher
from .interfaces import ISearchQuery
from .interfaces import IEntityIndexController

from nti.externalization.persistence import NoPickle

@interface.implementer(IIndexManager)
@NoPickle
class IndexManager(object):

	@classmethod
	def get_shared_indexmanager(cls):
		return component.getGlobalSiteManager().getUtility(IIndexManager)

	parallel_search = False

	def __init__(self, parallel_search=False):
		if parallel_search:
			self.parallel_search = parallel_search

	@classmethod
	def get_entity(cls, entity):
		result = Entity.get_entity(str(entity)) \
				 if not nti_interfaces.IEntity.providedBy(entity) else entity
		return result

	@classmethod
	def create_content_searcher(cls, *args, **kwargs):
		factory = component.getUtility(IContentSearcherFactory)
		result = factory(*args, **kwargs)
		return result

	@metric
	def search(self, query):
		query = search_query.QueryObject.create(query)
		results = search_results.empty_search_results(query)
		start = time.time()
		if self.parallel_search:
			greenlet = search_utils.gevent_spawn(func=self.user_data_search,
												 query=query,
									  			 store=results)
			cnt_results = self.content_search(query=query, store=results)
			ugd_results = greenlet.get()
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

	def register_content(self, ntiid=None, *args, **kwargs):
		# XXX Need a stronger contract for this method. It's not even in the interface
		# for the class, makes it hard to refactor away from knowledge about
		# whoosh-specific directories and layouts of content packages
		# (_indexmanager_event_listeners).

		if not ntiid:
			return False
		ntiid = ntiid.lower()

		sm = component.getSiteManager()
		searcher = sm.queryUtility(IContentSearcher,
								   name=ntiid)
		if searcher is not None:
			return searcher

		if self.parallel_search:
			kwargs['parallel_search'] = self.parallel_search

		searcher = self.create_content_searcher(ntiid=ntiid,
												*args, **kwargs)
		if searcher is not None:
			sm.registerUtility(searcher,
							   provided=IContentSearcher,
							   name=ntiid)
			logger.info("Content '%s' has been added to index manager", ntiid)
		else:
			logger.error("Content '%s' could not be added to index manager", ntiid)
		return searcher

	def unregister_content(self, ntiid):
		# Be careful to only unregister something found in the
		# current sitemanager. If nothing is registered at all,
		# return None. Otherwise, return True if we removed something
		# from this site manager, and False if we had nothing to remove
		# (meaning it was registered at a higher site)
		ntiid = ntiid.lower() if ntiid else ''

		sm = component.getSiteManager()
		searcher = sm.queryUtility(IContentSearcher,
								   name=ntiid)
		result = searcher
		if searcher is not None:
			result = sm.unregisterUtility(searcher,
										  provided=IContentSearcher,
										  name=ntiid)

		logger.info("Unregistered content '%s' from index manager? %s", ntiid, result)
		return result

	def get_content_searcher(self, query):
		name = query.indexid.lower() if query.indexid else ''
		searcher = component.queryUtility(IContentSearcher, name=name)
		return searcher

	def content_search(self, query, store=None):
		query = ISearchQuery(query)
		results = search_results.get_or_create_search_results(query, store)
		searcher = self.get_content_searcher(query)
		if searcher is not None:
			r = searcher.search(query, store=results)
			results = search_results.merge_search_results(results, r)
		return results

	def content_suggest_and_search(self, query, store=None):
		query = ISearchQuery(query)
		results = search_results.get_or_create_suggest_and_search_results(query, store)
		searcher = self.get_content_searcher(query)
		if searcher is not None:
			rs = searcher.suggest_and_search(query, store=results)
			results = search_results.merge_suggest_and_search_results(results, rs)
		return results

	def content_suggest(self, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		results = search_results.get_or_create_suggest_results(query, store)
		searcher = self.get_content_searcher(query)
		if searcher is not None:
			rs = searcher.suggest(query, store=results)
			results = search_results.merge_suggest_results(results, rs)
		return results

	def user_data_search(self, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		entity = self.get_entity(query.username)
		controller = IEntityIndexController(entity, None)
		results = controller.search(query, store=store) if controller is not None \
				  else search_results.empty_search_results(query)
		return results

	def user_data_suggest_and_search(self, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		entity = self.get_entity(query.username)
		controller = IEntityIndexController(entity, None)
		results = controller.suggest_and_search(query, store=store) \
				  if controller is not None \
				  else search_results.empty_suggest_and_search_results(query)
		return results

	def user_data_suggest(self, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		entity = self.get_entity(query.username)
		controller = IEntityIndexController(entity, None)
		results = controller.suggest(query, store=store) if controller is not None \
				  else search_results.empty_suggest_results(query)
		return results

	def index_user_content(self, target, data, *args, **kwargs):
		if data is not None:
			target = self.get_entity(target)
			controller = IEntityIndexController(target, None)
			if controller is not None:
				controller.index_content(data)

	def update_user_content(self, target, data, *args, **kwargs):
		if data is not None:
			target = self.get_entity(target)
			controller = IEntityIndexController(target, None)
			if controller is not None:
				controller.update_content(data)

	def delete_user_content(self, target, data, *args, **kwargs):
		if data is not None:
			target = self.get_entity(target)
			controller = IEntityIndexController(target, None)
			if controller is not None:
				controller.delete_content(data)

	def unindex(self, target, uid):
		target = self.get_entity(target)
		controller = IEntityIndexController(target, None)
		return controller.unindex(uid) if controller is not None else None

	def close(self):
		# In the past, this looked in `self.books`
		# for things to close, but there is no longer
		# any such attribute, so clearly this method was never
		# called.
		pass

@interface.implementer(IIndexManager)
def create_index_manager():
	return IndexManager(parallel_search=False)
