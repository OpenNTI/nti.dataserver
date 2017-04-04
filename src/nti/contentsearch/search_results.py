#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import time
import collections

from zope import component
from zope import interface

from zope.container.contained import Contained

from zope.mimetype.interfaces import IContentTypeAware

from nti.base._compat import unicode_

from nti.common.iterables import isorted

from nti.contentsearch.interfaces import ISearchResults
from nti.contentsearch.interfaces import ISuggestResults
from nti.contentsearch.interfaces import ISearchHitMetaData
from nti.contentsearch.interfaces import ISearchResultsList
from nti.contentsearch.interfaces import ISearchHitComparator
from nti.contentsearch.interfaces import ISearchHitComparatorFactory

from nti.property.property import alias

from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties


@interface.implementer(ISearchHitMetaData)
class SearchHitMetaData(object):

    unspecified_container = u'+++unspecified_container+++'

    __external_can_create__ = True
    mime_type = mimeType = u"application/vnd.nextthought.search.searchhitmetadata"

    filtered_count = 0
    SearchTime = lastModified = createdTime = 0

    def __init__(self):
        self._ref = time.time()
        self.filtering_predicates = set()
        self.type_count = collections.defaultdict(int)
        self.container_count = collections.defaultdict(int)

    def _get_type_count(self):
        return dict(self.type_count)

    def _set_type_count(self, tc):
        self.type_count.update(tc or {})
    TypeCount = property(_get_type_count, _set_type_count)

    def _get_container_count(self):
        return dict(self.container_count)

    def _set_container_count(self, cc):
        self.container_count.update(cc or {})
    ContainerCount = property(_get_container_count, _set_container_count)

    def _get_filtering_predicates(self):
        return set(self.filtering_predicates)

    def _set_filtering_predicates(self, cc):
        self.filtering_predicates.update(cc or ())
    FilteringPredicates = property(_get_filtering_predicates,
                                   _set_filtering_predicates)

    @property
    def TotalHitCount(self):
        return sum(self.type_count.values())

    def _get_filtered_count(self):
        return self.filtered_count

    def _set_filtered_count(self, count):
        self.filtered_count = count
    FilteredCount = property(_get_filtered_count, _set_filtered_count)

    def track(self, hit):
        self.SearchTime = time.time() - self._ref

        # container count
        containers = hit.Containers or (self.unspecified_container,)
        for cid in containers:
            self.container_count[cid] = self.container_count[cid] + 1

        lastModified = hit.lastModified or 0
        self.lastModified = max(self.lastModified, lastModified or 0)

        # type count
        type_name = hit.TargetMimeType or u'unknown'
        self.type_count[type_name] = self.type_count[type_name] + 1

    def __iadd__(self, other):
        # container count
        for k, v in other.container_count.items():
            self.container_count[k] = self.container_count[k] + v

        # last modified
        self.lastModified = max(self.lastModified, other.lastModified)

        # type count
        for k, v in other.type_count.items():
            self.type_count[k] = self.type_count[k] + v

        # search time
        self.SearchTime = max(self.SearchTime, other.SearchTime)

        # filtering predicates
        self.filtering_predicates.update(other.filtering_predicates)

        return self


class SearchResultsMixin(Contained):

    sorted = False
    parameters = {}

    Query = alias('query')
    Name = name = alias('__name__')

    def __init__(self, *args, **kwargs):
        super(SearchResultsMixin, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '%s(hits=%s)' % (self.__class__.__name__, len(self))
    __str__ = __repr__

    @property
    def Hits(self):
        return ()

    def __len__(self):
        return len(self.Hits)

    def __iter__(self):
        return iter(self.Hits)


@interface.implementer(ISearchResults, IContentTypeAware)
class SearchResults(SearchResultsMixin, SchemaConfigured):
    createDirectFieldProperties(ISearchResults)

    mime_type = mimeType = u"application/vnd.nextthought.search.searchresults"

    _hits = ()
    _count = 0
    _sorted = False
    HitMetaData = None

    metadata = alias('HitMetaData')

    def __init__(self, *args, **kwargs):
        hits = kwargs.pop('Hits', None)
        super(SearchResults, self).__init__(*args, **kwargs)
        self._count = 0
        self._hits = []
        self._seen = set()
        self.extend(hits or ())
        self.HitMetaData = SearchHitMetaData()

    def _raw_hits(self):
        return self._hits

    def _get_hits(self):
        if not self._sorted:
            self.sort()
        return self._hits

    def _set_hits(self, hits):
        for hit in hits or ():
            self._add_hit(hit)
    Hits = hits = property(_get_hits, _set_hits)

    def _get_lastModified(self):
        return self.HitMetaData.lastModified if self.HitMetaData else 0

    def _set_lastModified(self, v):
        pass
    lastModified = property(_get_lastModified, _set_lastModified)

    def _get_createdTime(self):
        return self.HitMetaData.createdTime if self.HitMetaData else 0

    def _set_createdTime(self, v):
        pass
    createdTime = property(_get_createdTime, _set_createdTime)

    def _add_hit(self, hit):
        if hit.ID not in self._seen:
            self._count += 1
            self._sorted = False
            self._hits.append(hit)
            self._seen.add(hit.ID)
            hit.__parent__ = self  # ownership
            return True
        return False

    def add_filter_record(self, item, predicate):
        self.metadata.filtered_count += 1
        name = getattr(predicate, '__name__', None) \
            or predicate.__class__.__name__
        self.metadata.filtering_predicates.add(name)

    def _add(self, hit):
        result = self._add_hit(hit)
        if result:
            self.metadata.track(hit)
        return result

    def add(self, hit):
        return self._add(hit)

    def extend(self, items):
        for item in items or ():
            self._add(item)

    def sort(self, sortOn=None):
        name = sortOn or (self.query.sortOn if self.query else u'')
        factory = component.queryUtility(ISearchHitComparatorFactory, name=name)
        comparator = factory(self) if factory is not None else None
        if comparator is not None:
            self._sorted = True
            reverse = not self.query.is_descending_sort_order
            self._hits.sort(comparator.compare, reverse=reverse)

    def __len__(self):
        return self._count

    def __iadd__(self, other):
        if ISearchResults.providedBy(other):
            self._set_hits(other._raw_hits())
            self.HitMetaData += other.HitMetaData
        return self


@interface.implementer(ISuggestResults, IContentTypeAware)
class SuggestResults(SearchResultsMixin, SchemaConfigured):
    createDirectFieldProperties(ISuggestResults)

    mime_type = mimeType = u"application/vnd.nextthought.search.suggestresults"

    _words = ()

    def __init__(self, *args, **kwargs):
        suggestions = kwargs.pop('Suggestions', None)
        super(SuggestResults, self).__init__(*args, **kwargs)
        self._words = set()
        self.extend(suggestions or ())

    def _get_words(self):
        return sorted(self._words)

    def _set_words(self, words):
        self._words.update(words or ())
    suggestions = Suggestions = property(_get_words, _set_words)

    def add(self, item):
        if isinstance(item, six.string_types):
            item = item.split()
        self.extend(item)
    add_suggestions = add

    def extend(self, items):
        self._words.update(unicode_(x) for x in items or ())

    def __iadd__(self, other):
        if ISuggestResults.providedBy(other):
            self._words.update(other.suggestions)
        return self

    def __len__(self):
        return len(self._words)

    def __iter__(self):
        return iter(self._words)


@interface.implementer(ISearchResultsList, IContentTypeAware)
class SearchResultsList(SchemaConfigured):
    createDirectFieldProperties(ISearchResultsList)

    mime_type = mimeType = u"application/vnd.nextthought.search.searchresultslist"

    _items = None

    def _get_items(self):
        return self._items or ()

    def _set_items(self, items):
        self._items = items
    items = Items = property(_get_items, _set_items)

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)

    @property
    def TotalHitCount(self):
        return sum(map(lambda x: len(x), self.items))
    NumFound = TotalHitCount

# sort


def sort_hits(hits, reverse=False, sortOn=None):
    comparator = component.queryUtility(ISearchHitComparator,
                                        name=sortOn) if sortOn else None
    if comparator is not None:
        if isinstance(hits, list):
            hits.sort(comparator.compare, reverse=reverse)
            return iter(hits)
        else:
            if reverse:
                comparator = lambda x, y: comparator(y, x)
            return isorted(hits, comparator)
    else:
        return reversed(hits) if reverse else iter(hits)
