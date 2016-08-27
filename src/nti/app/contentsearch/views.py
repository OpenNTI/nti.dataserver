#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from zope import interface

from zope.event import notify

from zope.location import locate

from z3c.batching.batch import Batch

from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.internalization import read_body_as_external_object
from nti.app.externalization.internalization import update_object_from_external_object

from nti.app.renderers.interfaces import IUncacheableInResponse

from nti.contentsearch.interfaces import IIndexManager
from nti.contentsearch.interfaces import ISearchResults
from nti.contentsearch.interfaces import SearchCompletedEvent
from nti.contentsearch.search_utils import create_queryobject

from nti.dataserver.users import Entity
from nti.dataserver.interfaces import IMemcacheClient

from nti.externalization.internalization import find_factory_for
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.externalization import to_external_object

from nti.property.property import Lazy
from nti.property.property import CachedProperty

ITEMS = StandardExternalFields.ITEMS

class BaseView(AbstractAuthenticatedView):

	name = None

	@classmethod
	def construct_queryobject(cls, request):
		username = request.matchdict.get('user', None)
		username = username or request.authenticated_userid
		params = dict(request.params)
		params['username'] = username
		params['term'] = request.matchdict.get('term', None)
		params['ntiid'] = request.matchdict.get('ntiid', None)
		params['site_names'] = getattr(request, 'possible_site_names', ()) or ('',)
		result = create_queryobject(username, params)
		return result

	@property
	def query(self):
		return self.construct_queryobject(self.request)

	@CachedProperty
	def indexmanager(self):
		return self.request.registry.getUtility(IIndexManager)

	def locate(self, obj, parent):
		# TODO: (Instead of modification info, we should be using etags here, anyway).
		locate(obj, parent, self.name)
		# TODO: Make cachable?
		interface.alsoProvides(obj, IUncacheableInResponse)
		return obj

	def search(self, query):
		raise NotImplementedError()

	def __call__(self):
		try:
			query = self.query
			result = self.search(query)
			result = self.locate(result, self.request.root)
			return result
		except ValueError as e:
			raise hexc.HTTPUnprocessableEntity(str(e))

class BaseSearchView(BaseView, BatchingUtilsMixin):

	def _batch_results(self, results, batch_size, batch_start):
		if 		batch_size is None \
			or 	batch_start is None \
			or	not ISearchResults.providedBy(results):
			response = (results, results, None)
		elif batch_start >= len(results):
			response = ((), results, None)
		else:
			new_results = results.clone(hits=False)
			batch_hits = Batch(results.Hits, batch_start, batch_size)
			new_results.Hits = batch_hits  # Set hits
			response = (new_results, results, batch_hits)
		return response

	def _do_search(self, query, store=None):
		result = self.indexmanager.search(query=query, store=store)
		return result

	def search(self, query):
		result = None
		now = time.time()
		# execute search
		result = self._do_search(query=query, store=result)

		# page if required
		batch_size, batch_start = self._get_batch_size_start()
		result, original, batch = self._batch_results(result, batch_size, batch_start)
		elapsed = time.time() - now

		# notify
		entity = Entity.get_entity(query.username)
		notify(SearchCompletedEvent(entity, original, elapsed))

		# externalize to add links
		result = to_external_object(result)
		if batch is not None:
			total_pages = len(original) // batch_size + 1
			result['BatchPage'] = batch_start // batch_size + 1
			result['ItemCount'] = len(result.get(ITEMS, ()))
			prev_batch_start, next_batch_start = self._batch_start_tuple(batch_start,
																		 batch_size)
			# check last page
			if total_pages == result['BatchPage']:
				next_batch_start = None
			self._create_batch_links(self.request, result,
									 next_batch_start, prev_batch_start)
		return result

class SearchView(BaseSearchView):
	name = 'Search'

	max_cache_time = 60
	max_cache_size = 50
	use_memcache = True

	DATA_BASE_KEY = "/search/%s/results/data"
	QUERY_BASE_KEY = "/search/%s/results/query"

	@Lazy
	def memcache(self):
		client = component.queryUtility(IMemcacheClient) if self.use_memcache else None
		return client

	@Lazy
	def _data_key(self):
		return self.DATA_BASE_KEY % self.remoteUser.username

	@Lazy
	def _query_key(self):
		return self.QUERY_BASE_KEY % self.remoteUser.username

	def _check_memcache(self, query):
		result = None
		client = self.memcache
		if client is None:
			return result
		try:
			data = client.get(self._query_key)
			if data:
				stored_query, stamp = data
				if 	stored_query.digest() == query.digest() and \
					time.time() - stamp < self.max_cache_time:
					result = client.get(self._data_key)
				else:
					client.delete(self._data_key)
					client.delete(self._query_key)
		except Exception as e:
			logger.error("Cannot get search result from Memcache. %s", e)
			result = None
		return result

	def _store_memcache(self, query, results):
		client = self.memcache
		if client is None:
			return
		try:
			data = (query, time.time())
			client.set(self._query_key, data)
			client.set(self._data_key, results)
		except Exception as e:
			logger.error("Cannot store results in Memcache. %s", e)

	def _do_search(self, query, store=None):
		result = self._check_memcache(query)
		if result is None:
			result = self.indexmanager.search(query=query, store=store)
			if len(result) >= self.max_cache_size:
				self._store_memcache(query, result)
		return result

Search = SearchView  # BWC

class UserDataSearchView(BaseSearchView):
	name = 'UserSearch'
UserSearch = UserDataSearchView  # BWC

class SuggestView(BaseView):
	name = 'Suggest'

	def _do_search(self, query, store=None):
		result = self.indexmanager.suggest(query=query, store=store)
		return result

	def search(self, *queries):
		result = None
		now = time.time()
		for query in queries:
			result = self._do_search(query=query, store=result)
		elapsed = time.time() - now
		entity = Entity.get_entity(query.username)
		notify(SearchCompletedEvent(entity, result, elapsed))
		return result
Suggest = SuggestView  # BWC

class HighlightSearchHitsView(AbstractAuthenticatedView):

	def readInput(self):
		return read_body_as_external_object(self.request)

	def createResults(self):
		externalValue = self.readInput()
		result = find_factory_for(externalValue)
		result = result() if result else None
		if not ISearchResults.providedBy(result):
			raise hexc.HTTPBadRequest(detail="invalid type")
		update_object_from_external_object(result, externalValue)
		return result

	def __call__(self):
		result = self.createResults()
		result.Query.applyHighlights = True
		for hit in result.Hits:  # make sure we null out Fragments field
			hit.Fragments = None
		return result
HighlightResults = HighlightSearchHitsView  # BWC
