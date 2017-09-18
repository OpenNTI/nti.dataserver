#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
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

from nti.app.contentsearch import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.renderers.interfaces import IUncacheableInResponse

from nti.contentsearch.interfaces import ISearcher
from nti.contentsearch.interfaces import ISearchHitPredicate
from nti.contentsearch.interfaces import SearchCompletedEvent
from nti.contentsearch.interfaces import ISearchQueryValidator

from nti.contentsearch.search_results import SearchResults
from nti.contentsearch.search_results import SuggestResults

from nti.contentsearch.search_utils import create_queryobject

from nti.dataserver.users.entity import Entity

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS


class BaseView(AbstractAuthenticatedView):

    _DEFAULT_BATCH_SIZE = 10
    _DEFAULT_BATCH_START = 0

    name = None

    @classmethod
    def construct_queryobject(cls, request):
        username = request.matchdict.get('user', None)
        username = username or request.authenticated_userid
        params = dict(request.params)
        params['username'] = username
        params['term'] = request.matchdict.get('term', None)
        params['ntiid'] = request.matchdict.get('ntiid', None)
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
            logger.exception("Cannot execute search query")
            exc_info = sys.exc_info()
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Cannot execute search query.'),
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
            logger.exception("Invalid search query")
            exc_info = sys.exc_info()
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Invalid search query.'),
                                 'field': 'term',
                                 'code': e.__class__.__name__
                             },
                             exc_info[2])

    def _search_func(self, searcher):
        return searcher.search

    def _do_search(self, query, batch_size, batch_start):
        # First batch, we want all items up to batchSize (0 - batchSize).
        # This will make sure our batchStart lines up, especially if
        # we have multiple catalogs.
        next_search_start = 0
        self.search_hit_count = 0
        searcher = ISearcher(self.remoteUser, None)
        if searcher is not None:
            search_func = self._search_func(searcher)
            while True:
                for item in search_func(query=query,
                                        batch_start=next_search_start,
                                        batch_size=batch_size):
                    if self.search_hit_count >= batch_start:
                        # Do not start returning until we get to our batchStart
                        yield item
                    self.search_hit_count += 1
                if self.search_hit_count < next_search_start + batch_size:
                    # Our searcher ran out of hits
                    break
                # Otherwise, fetch the next batch
                next_search_start += batch_size

    def _include_item(self, hit, search_results):
        """
        Ping our ISearchPredicates to see if this hit is
        applicable to our remote user.
        """
        if hit is None:
            return False
        item, score, query = hit.Target, hit.Score, self.query
        for predicate in component.subscribers((item,), ISearchHitPredicate):
            if not predicate.allow(item, score, query):
                search_results.add_filter_record(item, predicate)
                return False
        return search_results.add(hit)

    def _get_results(self, query):
        return SearchResults(Query=query)

    def search(self, query):
        now = time.time()
        search_results = self._get_results(query)
        batch_size, batch_start = self._get_batch_size_start()
        for hit in self._do_search(query, batch_size, batch_start):
            if self._include_item(hit, search_results):
                if len(search_results) >= batch_size:
                    break

        elapsed = time.time() - now
        entity = Entity.get_entity(query.username)
        notify(SearchCompletedEvent(entity, search_results, elapsed))
        ext_obj = to_external_object(search_results)
        # Since we index based on solr count, this makes it really hard
        # to get the previous batch number (we could store our current
        # batch-start on the 'next' link for future use).
        if len(search_results) >= batch_size:
            BatchingUtilsMixin._create_batch_links(self.request,
                                                   ext_obj,
                                                   self.search_hit_count + 1,
                                                   None)
        return ext_obj


class SearchView(BaseSearchView):
    name = u'Search'


Search = SearchView  # BWC


class UserDataSearchView(BaseSearchView):
    name = u'UserSearch'


UserSearch = UserDataSearchView  # BWC


class SuggestView(BaseView):
    name = 'uSuggest'

    def _include_item(self, hit, search_results):
        # No need to filter suggestions.
        return search_results.add(hit)

    def _get_results(self, query):
        return SuggestResults(Name="Suggestions", Query=query)

    def _search_func(self, searcher):
        return searcher.suggest


Suggest = SuggestView  # BWC
