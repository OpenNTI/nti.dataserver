#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import interface

from zope.event import notify

from zope.location import locate

from z3c.batching.batch import Batch

from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.renderers.interfaces import IUncacheableInResponse

from nti.contentsearch.interfaces import ISearcher 
from nti.contentsearch.interfaces import ISearchResults
from nti.contentsearch.interfaces import ISuggestResults 
from nti.contentsearch.interfaces import SearchCompletedEvent

from nti.contentsearch.search_utils import create_queryobject

from nti.dataserver.users import Entity

from nti.externalization.interfaces import LocatedExternalList
from nti.externalization.interfaces import StandardExternalFields

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

	def locate(self, obj, parent):
		locate(obj, parent, self.name)
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

	def _do_search(self, query):
		searcher = ISearcher(self.remoteUser)
		result = searcher.search(query=query)
		return (result,) if ISearchResults.providedBy(result) else result

	def search(self, query):
		now = time.time()
		# execute search
		result = self._do_search(query=query)

# 		# page if required
# 		batch_size, batch_start = self._get_batch_size_start()
# 		result, original, batch = self._batch_results(result, batch_size, batch_start)
		elapsed = time.time() - now
# 
		# notify
		entity = Entity.get_entity(query.username)
#		notify(SearchCompletedEvent(entity, result, elapsed))
# 
# 		# externalize to add links
# 		result = to_external_object(result)
# 		if batch is not None:
# 			total_pages = len(original) // batch_size + 1
# 			result['BatchPage'] = batch_start // batch_size + 1
# 			result['ItemCount'] = len(result.get(ITEMS, ()))
# 			prev_batch_start, next_batch_start = self._batch_start_tuple(batch_start,
# 																		 batch_size)
# 			# check last page
# 			if total_pages == result['BatchPage']:
# 				next_batch_start = None
# 			self._create_batch_links(self.request, result,
# 									 next_batch_start, prev_batch_start)
		return result

class SearchView(BaseSearchView):
	name = 'Search'

Search = SearchView  # BWC

class UserDataSearchView(BaseSearchView):
	name = 'UserSearch'
UserSearch = UserDataSearchView  # BWC

class SuggestView(BaseView):
	name = 'Suggest'

	def _do_search(self, query):
		searcher = ISearcher(self.remoteUser)
		result = searcher.suggest(query=query)
		return (result,) if ISuggestResults.providedBy(result) else result

	def search(self, *queries):
		now = time.time()
		result = LocatedExternalList()
		for query in queries:
			result.extend(self._do_search(query=query))
		elapsed = time.time() - now
		entity = Entity.get_entity(query.username)
		notify(SearchCompletedEvent(entity, result, elapsed))
		return result
Suggest = SuggestView  # BWC
