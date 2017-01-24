#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.contentsearch.interfaces import ISearchQuery
from nti.contentsearch.interfaces import ISearchResults
from nti.contentsearch.interfaces import ISuggestResults
from nti.contentsearch.interfaces import ISearchHitMetaData

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectUpdater
from nti.externalization.interfaces import StandardExternalFields

QUERY = 'Query'
SEARCH_QUERY = 'SearchQuery'
TOTAL = StandardExternalFields.TOTAL
ITEMS = StandardExternalFields.ITEMS


@component.adapter(ISearchQuery)
@interface.implementer(IInternalObjectUpdater)
class _QueryObjectUpdater(object):

    __slots__ = ('obj',)

    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        result = InterfaceObjectIO(self.obj,
								   ISearchQuery).updateFromExternalObject(parsed)
        return result


@component.adapter(ISearchHitMetaData)
@interface.implementer(IInternalObjectUpdater)
class _SearchHitMetaDataUpdater(object):

    __slots__ = ('obj',)

    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        parsed.pop('TotalHitCount', None) # readonly
        parsed['FilteringPredicates'] = set(parsed.pop('FilteringPredicates', ()))
        result = InterfaceObjectIO(self.obj,
                                   ISearchHitMetaData).updateFromExternalObject(parsed)
        return result


@interface.implementer(IInternalObjectUpdater)
class _SearchResultsUpdater(object):

    __slots__ = ('obj',)

    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        if ITEMS in parsed:
            parsed['Hits'] = parsed.pop(ITEMS, ())

        if TOTAL in parsed:
            parsed['NumFound'] = parsed.pop(TOTAL, None)

        if SEARCH_QUERY in parsed:
            parsed[QUERY] = parsed.pop(SEARCH_QUERY, None)

        result = InterfaceObjectIO(self.obj,
								   ISearchResults).updateFromExternalObject(parsed)
        return result


@interface.implementer(IInternalObjectUpdater)
@component.adapter(ISuggestResults)
class _SuggestResultsUpdater(object):

    __slots__ = ('obj',)

    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        if ITEMS in parsed:
            parsed['Suggestions'] = parsed.pop(ITEMS, ())
        if SEARCH_QUERY in parsed:
            parsed[QUERY] = parsed.pop(SEARCH_QUERY, None)
        result = InterfaceObjectIO(self.obj,
                                   ISuggestResults).updateFromExternalObject(parsed)
        return result
