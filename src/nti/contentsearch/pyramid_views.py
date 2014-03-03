#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import interface
from zope.event import notify
from zope.location import locate

from z3c.batching.batch import Batch

from nti.app.renderers import interfaces as app_interfaces
from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.dataserver.users import Entity

from . import search_utils
from . import interfaces as search_interfaces

class BaseView(object):

	name = None

	def __init__(self, request):
		self.request = request

	@property
	def query(self):
		return search_utils.construct_queryobject(self.request)

	@property
	def indexmanager(self):
		return self.request.registry.getUtility(search_interfaces.IIndexManager)

	def locate(self, obj, parent):
		# TODO: (Instead of modification info, we should be using etags here, anyway).
		locate(obj, parent, self.name)
		# TODO: Make cachable?
		interface.alsoProvides(obj, app_interfaces.IUncacheableInResponse)
		return obj

	def search(self, query):
		raise NotImplementedError()

	def __call__(self):
		query = self.query
		result = self.search(query=query)
		result = self.locate(result, self.request.root)
		return result

class BaseSearchView(BaseView,
					 BatchingUtilsMixin):

	def _batch_results(self, results):
		batch_size, batch_start = self._get_batch_size_start()
		if 	batch_size is None or batch_start is None or \
			not search_interfaces.ISearchResults.providedBy(results):
			return results, results
		else:
			new_results = results.clone(hits=False)
			if batch_start < len(results):
				batch_hits = Batch(results.Hits, batch_start, batch_size)
				new_results.Hits = batch_hits  # Set hits this iterates
				# this is a bit hackish, but it avoids building a new
				# batch object plus the link decorator needs the orignal
				# batch object
				new_results.Batch = batch_hits  # save for decorator
			return new_results, results

	def search(self, query):
		now = time.time()
		result = self.indexmanager.search(query=query)
		result, original = self._batch_results(result)
		elapsed = time.time() - now
		entity = Entity.get_entity(query.username)
		notify(search_interfaces.SearchCompletedEvent(entity, original, elapsed))
		return result

class SearchView(BaseSearchView):
	name = 'Search'
Search = SearchView  # BWC

class UserDataSearchView(BaseSearchView):
	name = 'UserSearch'
UserSearch = UserDataSearchView  # BWC

class SuggestView(BaseView):
	name = 'Suggest'

	def search(self, query):
		now = time.time()
		result = self.indexmanager.suggest(query=query)
		elapsed = time.time() - now
		entity = Entity.get_entity(query.username)
		notify(search_interfaces.SearchCompletedEvent(entity, result, elapsed))
		return result
Suggest = SuggestView  # BWC
