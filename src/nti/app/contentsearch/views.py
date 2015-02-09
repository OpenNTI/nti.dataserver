#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search pyramid views.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import interface
from zope.event import notify
from zope.location import locate

from pyramid import httpexceptions as hexc

from z3c.batching.batch import Batch

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.internalization import read_body_as_external_object
from nti.app.externalization.internalization import update_object_from_external_object

from nti.app.renderers.interfaces import IUncacheableInResponse

from nti.common.property import CachedProperty

from nti.contentsearch.interfaces import IIndexManager
from nti.contentsearch.interfaces import ISearchResults
from nti.contentsearch.interfaces import SearchCompletedEvent
from nti.contentsearch.search_utils import construct_queryobject

from nti.dataserver.users import Entity

from nti.externalization.internalization import find_factory_for

class BaseView(AbstractAuthenticatedView):

	name = None

	@property
	def query(self):
		return construct_queryobject(self.request)

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
		query = self.query
		result = self.search(query)
		result = self.locate(result, self.request.root)
		return result

class BaseSearchView(BaseView,
					 BatchingUtilsMixin):

	def _batch_results(self, results):
		batch_size, batch_start = self._get_batch_size_start()
		if 	batch_size is None or batch_start is None or \
			not ISearchResults.providedBy(results):
			return results, results

		new_results = results.clone(hits=False)
		if batch_start < len(results):
			batch_hits = Batch(results.Hits, batch_start, batch_size)
			new_results.Hits = batch_hits  # Set hits this iterates
			# this is a bit hackish, but it avoids building a new
			# batch object plus the link decorator needs the orignal
			# batch object
			new_results.Batch = batch_hits  # save for decorator
		return new_results, results

	def _do_search(self, query, store=None):
		result = self.indexmanager.search(query=query, store=store)
		return result
	
	def search(self, *queries):
		result = None
		now = time.time()
		for query in queries:
			result = self._do_search(query=query, store=result)
		result, original = self._batch_results(result)
		elapsed = time.time() - now
		entity = Entity.get_entity(query.username)
		notify(SearchCompletedEvent(entity, original, elapsed))
		return result

class SearchView(BaseSearchView):
	name = 'Search'
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
