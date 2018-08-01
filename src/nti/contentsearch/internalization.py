#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.contentsearch.interfaces import ISearchQuery
from nti.contentsearch.interfaces import ISearchResults
from nti.contentsearch.interfaces import ISuggestResults
from nti.contentsearch.interfaces import ISearchHitMetaData

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectUpdater
from nti.externalization.interfaces import StandardExternalFields

QUERY = u'Query'
SEARCH_QUERY = u'SearchQuery'
TOTAL = StandardExternalFields.TOTAL
ITEMS = StandardExternalFields.ITEMS

logger = __import__('logging').getLogger(__name__)


@component.adapter(ISearchQuery)
@interface.implementer(IInternalObjectUpdater)
class _QueryObjectUpdater(object):

    __slots__ = ('obj',)

    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        result = InterfaceObjectIO(self.obj,
                                   ISearchQuery).updateFromExternalObject(parsed)
        return result


@component.adapter(ISearchHitMetaData)
@interface.implementer(IInternalObjectUpdater)
class _SearchHitMetaDataUpdater(object):

    __slots__ = ('obj',)

    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        parsed.pop('TotalHitCount', None)  # readonly
        parsed['FilteringPredicates'] = dict(parsed.pop('FilteringPredicates', {}))
        result = InterfaceObjectIO(
                    self.obj,
                    ISearchHitMetaData).updateFromExternalObject(parsed)
        return result


@interface.implementer(IInternalObjectUpdater)
class _SearchResultsUpdater(object):

    __slots__ = ('obj',)

    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        if ITEMS in parsed:
            parsed['Hits'] = parsed.pop(ITEMS, ())

        if TOTAL in parsed:
            parsed['NumFound'] = parsed.pop(TOTAL, None)

        if SEARCH_QUERY in parsed:
            parsed[QUERY] = parsed.pop(SEARCH_QUERY, None)

        result = InterfaceObjectIO(
                    self.obj,
                    ISearchResults).updateFromExternalObject(parsed)
        return result


@interface.implementer(IInternalObjectUpdater)
@component.adapter(ISuggestResults)
class _SuggestResultsUpdater(object):

    __slots__ = ('obj',)

    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        if ITEMS in parsed:
            parsed['Suggestions'] = parsed.pop(ITEMS, ())
        if SEARCH_QUERY in parsed:
            parsed[QUERY] = parsed.pop(SEARCH_QUERY, None)
        result = InterfaceObjectIO(
                    self.obj,
                    ISuggestResults).updateFromExternalObject(parsed)
        return result
