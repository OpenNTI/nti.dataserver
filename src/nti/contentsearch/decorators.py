#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
... $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.contentsearch.interfaces import ISearchResults
from nti.contentsearch.interfaces import ISuggestResults
from nti.contentsearch.interfaces import ISearchHitMetaData
from nti.contentsearch.interfaces import ISearchResultsList

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator

from nti.externalization.singleton import Singleton

QUERY = 'Query'
HIT_COUNT = 'HitCount'
SEARCH_QUERY = 'SearchQuery'
ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT
CREATED_TIME = StandardExternalFields.CREATED_TIME

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IExternalObjectDecorator)
class _ResultsDecorator(Singleton):

    def decorateCommon(self, original, external):
        external.pop(CREATED_TIME, None)
        external[SEARCH_QUERY] = external[QUERY]
        external[QUERY] = original.Query.term
        external[ITEM_COUNT] = len(external[ITEMS])

    def decorateExternalObject(self, original, external):
        external[ITEMS] = external.pop('Hits', [])
        self.decorateCommon(original, external)


@component.adapter(ISearchResults)
class _SearchResultsDecorator(_ResultsDecorator):
    pass


@component.adapter(ISuggestResults)
class _SuggestResultsDecorator(_ResultsDecorator):

    def decorateExternalObject(self, original, external):
        external[ITEMS] = external.pop('Suggestions', [])
        self.decorateCommon(original, external)


@component.adapter(ISearchHitMetaData)
class _SearchHitMetaDataDecorator(Singleton):

    def decorateExternalObject(self, unused_original, external):
        external.pop(CREATED_TIME, None)


@component.adapter(ISearchResultsList)
class _SearchResultsListDecorator(Singleton):

    def decorateExternalObject(self, original, external):
        external[TOTAL] = external[ITEM_COUNT] = len(original)
