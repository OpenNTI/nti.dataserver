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
from nti.dataserver.interfaces import IEntity

from nti.externalization.persistence import NoPickle

from nti.site.interfaces import IHostPolicySiteManager

from .search_query import QueryObject

from .search_utils import gevent_spawn

from .interfaces import ISearchQuery
from .interfaces import IIndexManager
from .interfaces import IContentSearcher
from .interfaces import IEntityIndexController
from .interfaces import IContentSearcherFactory

from .search_results import empty_search_results
from .search_results import merge_search_results
from .search_results import empty_suggest_results
from .search_results import merge_suggest_results
from .search_results import get_or_create_search_results
from .search_results import get_or_create_suggest_results
from .search_results import empty_suggest_and_search_results
from .search_results import merge_suggest_and_search_results
from .search_results import get_or_create_suggest_and_search_results

@interface.implementer(IIndexManager)
@NoPickle
class IndexManager(object):

	parallel_search = False

	def __init__(self, parallel_search=False):
		if parallel_search:
			self.parallel_search = parallel_search

	@classmethod
	def get_entity(cls, entity):
		result = Entity.get_entity(str(entity)) \
				 if not IEntity.providedBy(entity) else entity
		return result

	@classmethod
	def create_content_searcher(cls, *args, **kwargs):
		factory = component.getUtility(IContentSearcherFactory)
		result = factory(*args, **kwargs)
		return result

	@metric
	def search(self, query, store=None):
		query = QueryObject.create(query)
		results = get_or_create_search_results(query, store)
		start = time.time()
		if self.parallel_search:
			greenlet = gevent_spawn(func=self.user_data_search,
									query=query,
									store=results)
			cnt_results = self.content_search(query=query, store=results)
			ugd_results = greenlet.get()
		else:
			cnt_results = self.content_search(query=query, store=results)
			ugd_results = self.user_data_search(query=query, store=results)
		results = merge_search_results(cnt_results, ugd_results)
		logger.debug("Query '%s' returned %s hit(s). Took %.3f(secs)",
					 query, len(results), time.time() - start)
		return results

	@metric
	def suggest_and_search(self, query, store=None):
		query = QueryObject.create(query)
		results = get_or_create_suggest_and_search_results(query, store)
		cnt_data = self.content_suggest_and_search(query=query, store=results)
		ugd_data = self.user_data_suggest_and_search(query=query, store=results)
		results = merge_suggest_and_search_results(cnt_data, ugd_data)
		return results

	@metric
	def suggest(self, query, store=None):
		query = QueryObject.create(query)
		results = get_or_create_suggest_results(query, store)
		cnt_results = self.content_suggest(query=query, store=results)
		ugd_results = self.user_data_suggest(query=query, store=results)
		results = merge_suggest_results(cnt_results, ugd_results)
		return results

	def register_content(self, ntiid=None, indexname=None, indexdir=None,
						 parallel_search=False, *args, **kwargs):
		"""
		Register the content by ntiid in the current site if it is not
		already registered in the current site.

		If the current site is NOT a host policy site, register instead in the
		global site (because we probably do not get the events that allow
		us to unregister for anything except host policy sites)
		"""
		if not ntiid:
			return False
		ntiid = ntiid.lower()

		sm = component.getSiteManager()
		if not IHostPolicySiteManager.providedBy(sm):
			sm = component.getGlobalSiteManager()

		searcher = sm.queryUtility(IContentSearcher, name=ntiid)
		if searcher is not None and getattr(searcher, '__parent__', None) == sm:
			# Don't re-register, IF we're already registered at this
			# level; if we're registered somewhere higher, we need to
			# register here to override the parent. (Old searchers have no __parent__)
			return searcher

		if self.parallel_search:
			kwargs['parallel_search'] = self.parallel_search

		searcher = self.create_content_searcher(ntiid=ntiid,
												indexdir=indexdir,
												indexname=indexname,
												*args, **kwargs)
		if searcher is not None:
			searcher.__parent__ = sm
			searcher.__name__ = ntiid
			sm.registerUtility(searcher,
							   		provided=IContentSearcher,
							   		name=ntiid)
			logger.info("Content '%s' has been added to index manager in site %s",
						ntiid, sm)
		else:
			logger.error("Content '%s' could not be added to index manager", ntiid)
		return searcher

	def unregister_content(self, ntiid):
		# Be careful to only unregister something found in the
		# current sitemanager. If nothing is registered at all,
		# return None. Otherwise, return True if we removed something
		# from this site manager, and False if we had nothing to remove
		# (meaning it was registered at a higher site).
		# Special case for unregistering something only registered globally
		# if we're currently in a subsite.
		ntiid = ntiid.lower() if ntiid else ''

		sm = component.getSiteManager()
		searcher = sm.queryUtility(IContentSearcher,
								   name=ntiid)
		result = searcher
		if searcher is not None:
			if getattr(searcher, '__parent__', sm) == component.getGlobalSiteManager():
				sm = component.getGlobalSiteManager()
			result = sm.unregisterUtility(searcher,
										  provided=IContentSearcher,
										  name=ntiid)

		logger.info("Unregistered content '%s' from index manager and site %s? %s",
					ntiid, sm, result)
		return result

	def get_content_searchers(self, query):
		for name in query.packages or ():
			name = name.lower() if name else ''
			searcher = component.queryUtility(IContentSearcher, name=name)
			if searcher is not None:
				yield searcher

	def content_search(self, query, store=None):
		query = ISearchQuery(query)
		results = get_or_create_search_results(query, store)
		for searcher in self.get_content_searchers(query):
			r = searcher.search(query, store=results)
			results = merge_search_results(results, r)
		return results

	def content_suggest_and_search(self, query, store=None):
		query = ISearchQuery(query)
		results = get_or_create_suggest_and_search_results(query, store)
		for searcher in self.get_content_searchers(query):
			rs = searcher.suggest_and_search(query, store=results)
			results = merge_suggest_and_search_results(results, rs)
		return results

	def content_suggest(self, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		results = get_or_create_suggest_results(query, store)
		for searcher in self.get_content_searchers(query):
			rs = searcher.suggest(query, store=results)
			results = merge_suggest_results(results, rs)
		return results

	def user_data_search(self, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		entity = self.get_entity(query.username)
		controller = IEntityIndexController(entity, None)
		results = controller.search(query, store=store) if controller is not None \
				  else empty_search_results(query)
		return results

	def user_data_suggest_and_search(self, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		entity = self.get_entity(query.username)
		controller = IEntityIndexController(entity, None)
		results = controller.suggest_and_search(query, store=store) \
				  if controller is not None \
				  else empty_suggest_and_search_results(query)
		return results

	def user_data_suggest(self, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		entity = self.get_entity(query.username)
		controller = IEntityIndexController(entity, None)
		results = controller.suggest(query, store=store) if controller is not None \
				  else empty_suggest_results(query)
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
