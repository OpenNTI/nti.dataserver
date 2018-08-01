#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.contentsearch.interfaces import ISearchHit
from nti.contentsearch.interfaces import ISearchHitComparator
from nti.contentsearch.interfaces import ISearchHitComparatorFactory

logger = __import__('logging').getLogger(__name__)


class _CallableComparator(object):

    def __init__(self, results=None):
        self.results = results

    def __call__(self, a, b):
        return self.compare(a, b)

    def compare(self, a, b):
        raise NotImplementedError()


@interface.implementer(ISearchHitComparator)
class _ScoreSearchHitComparator(_CallableComparator):

    @classmethod
    def get_score(cls, item):
        result = None
        if ISearchHit.providedBy(item):
            result = item.Score
        return result or 1.0

    @classmethod
    def compare_score(cls, a, b):
        a_score = cls.get_score(a)
        b_score = cls.get_score(b)
        return cmp(b_score, a_score)

    @classmethod
    def compare(cls, a, b):
        return cls.compare_score(a, b)


@interface.implementer(ISearchHitComparatorFactory)
class _ScoreSearchHitComparatorFactory(object):

    singleton = _ScoreSearchHitComparator()

    def __call__(self, unused_results=None):
        return self.singleton


@interface.implementer(ISearchHitComparator)
class _LastModifiedSearchHitComparator(_CallableComparator):

    @classmethod
    def get_lm(cls, item):
        if ISearchHit.providedBy(item) or hasattr(item, 'lastModified'):
            return item.lastModified
        return 0

    @classmethod
    def compare_lm(cls, a, b):
        a_lm = cls.get_lm(a)
        b_lm = cls.get_lm(b)
        return cmp(a_lm, b_lm)

    @classmethod
    def compare(cls, a, b):
        return cls.compare_lm(a, b)


@interface.implementer(ISearchHitComparatorFactory)
class _LastModifiedSearchHitComparatorFactory(object):

    singleton = _LastModifiedSearchHitComparator()

    def __call__(self, unused_results=None):
        return self.singleton


@interface.implementer(ISearchHitComparator)
class _CreatorSearchHitComparator(_ScoreSearchHitComparator,
                                  _LastModifiedSearchHitComparator):

    @classmethod
    def compare_creator(cls, a, b):
        a_creator = a.Creator or u''
        b_creator = b.Creator or u''
        return cmp(a_creator.lower(), b_creator.lower())

    @classmethod
    def compare(cls, a, b):
        result = cls.compare_creator(a, b)
        if result == 0:
            result = cls.compare_lm(b, a)  # more recent first
        if result == 0:
            result = cls.compare_score(a, b)
        return result


@interface.implementer(ISearchHitComparatorFactory)
class _CreatorSearchHitComparatorFactory(object):

    singleton = _CreatorSearchHitComparator()

    def __call__(self, unused_results=None):
        return self.singleton
