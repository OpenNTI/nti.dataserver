#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import time

from zope import component
from zope import interface

from zope.event import notify

from zope.location import locate

from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.renderers.interfaces import IUncacheableInResponse

from nti.contentsearch.interfaces import ISearcher
from nti.contentsearch.interfaces import SearchCompletedEvent
from nti.contentsearch.interfaces import ISearchQueryValidator

from nti.contentsearch.search_results import SearchResultsList

from nti.contentsearch.search_utils import create_queryobject

from nti.dataserver.users import Entity

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
			exc_info = sys.exc_info()
			raise_json_error(
						self.request,
					  	hexc.HTTPUnprocessableEntity,
					  	{ 
							'message': _('Cannot execute search query.'),
							'field': 'term',
							'code': e.__class__.__name__ 
						},
					  	exc_info[2])

class BaseSearchView(BaseView, BatchingUtilsMixin):

	def _validate(self, query):
		try:
			validator = component.queryUtility(ISearchQueryValidator)
			if validator is not None:
				validator.validate(query)
		except Exception as e:
			exc_info = sys.exc_info()
			raise_json_error(
						self.request,
					  	hexc.HTTPUnprocessableEntity,
					  	{ 
							'message': _('Invalid search query.'),
							'field': 'term',
							'code': e.__class__.__name__ 
						},
					  	exc_info[2])

	def _do_search(self, query):
		searcher = ISearcher(self.remoteUser, None)
		if searcher is not None:
			return searcher.search(query=query)
		return SearchResultsList(Query=query)

	def search(self, query):
		now = time.time()
		result = self._do_search(query=query)
		elapsed = time.time() - now
		entity = Entity.get_entity(query.username)
		notify(SearchCompletedEvent(entity, result, elapsed))
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
		searcher = ISearcher(self.remoteUser, None)
		if searcher is not None:
			return searcher.suggest(query=query)
		return SearchResultsList(Query=query)

	def search(self, query):
		now = time.time()
		result = self._do_search(query)
		elapsed = time.time() - now
		entity = Entity.get_entity(query.username)
		notify(SearchCompletedEvent(entity, result, elapsed))
		return result
Suggest = SuggestView  # BWC
