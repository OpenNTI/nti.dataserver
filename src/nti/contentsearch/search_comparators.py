#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import math
from datetime import datetime

from zope import interface

import repoze.lru

from nti.contentsearch.common import get_sort_order

from nti.contentsearch.content_utils import get_ntiid_path as content_ntiid_path

from nti.contentsearch.interfaces import ISearchHit
from nti.contentsearch.interfaces import ISearchHitComparator
from nti.contentsearch.interfaces import ISearchHitComparatorFactory

from nti.ntiids import ntiids

from nti.property.property import Lazy

class _CallableComparator(object):

	def __init__(self, results=None):
		self.results = results

	def __call__(self, a, b):
		return self.compare(a, b)

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

	def __call__(self, results=None):
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

	def __call__(self, results=None):
		return self.singleton

@interface.implementer(ISearchHitComparator)
class _TypeSearchHitComparator(_ScoreSearchHitComparator,
							   _LastModifiedSearchHitComparator):

	@classmethod
	def get_type_name(cls, item):
		result = item.Type if ISearchHit.providedBy(item) else u''
		return result or u''

	@classmethod
	def compare_type(cls, a, b):
		a_order = get_sort_order(cls.get_type_name(a))
		b_order = get_sort_order(cls.get_type_name(b))
		return cmp(a_order, b_order)

	@classmethod
	def compare(cls, a, b):
		result = cls.compare_type(a, b)
		if result == 0:
			result = cls.compare_lm(a, b)
		if result == 0:
			result = cls.compare_score(a, b)
		return result

@interface.implementer(ISearchHitComparatorFactory)
class _TypeSearchHitComparatorFactory(object):

	singleton = _TypeSearchHitComparator()

	def __call__(self, results=None):
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

	def __call__(self, results=None):
		return self.singleton

@interface.implementer(ISearchHitComparator)
class _DecayFactorSearchHitComparator(_CallableComparator):

	def __init__(self, results):
		super(_DecayFactorSearchHitComparator, self).__init__(results)
		self.now = datetime.now()

	@Lazy
	def decay(self):
		query = self.results.Query
		return getattr(query, 'decayFactor', 0.94)

	def factor(self, item):
		return item.Score or 1.0

	def _score(self, item, use_hours=False):
		delta = self.now - datetime.fromtimestamp(item.lastModified)
		x = delta.days if not use_hours else delta.total_seconds() / 60.0 / 60.0
		return math.pow(self.decay, x) * self.factor(item)

	def compare(self, a, b):
		a_score = self._score(a)
		b_score = self._score(b)
		return cmp(a_score, b_score)

@interface.implementer(ISearchHitComparatorFactory)
class _DecaySearchHitComparatorFactory(object):

	__slots__ = ()

	def __call__(self, results):
		return _DecayFactorSearchHitComparator(results)

@repoze.lru.lru_cache(maxsize=2000, timeout=60)
def _path_intersection(x, y):
	result = []
	stop = min(len(x), len(y))
	for i in xrange(0, stop):
		if x[i] == y[i]:
			result.append(x[i])
		else:
			break
	return tuple(result) if result else ()

@repoze.lru.lru_cache(maxsize=2000, timeout=60)
def get_ntiid_path(item):
	result = content_ntiid_path(item)
	return result

@interface.implementer(ISearchHitComparator)
class _RelevanceSearchHitComparator(_TypeSearchHitComparator):

	IGNORED_TYPES = {ntiids.TYPE_OID, ntiids.TYPE_UUID, ntiids.TYPE_INTID,
					 ntiids.TYPE_MEETINGROOM}

	@classmethod
	def score_path(cls, reference, p):

		if not reference or not p:
			return 0

		ip = _path_intersection(reference, p)
		if len(ip) == 0:
			result = 0  # no path intersection
		elif len(ip) == len(reference):
			if len(reference) == len(p):
				result = 10000  # give max priority to hits int the same location
			else:
				result = 9000  # hit is below
		elif len(ip) == len(p):  # p is n a subset of ref
			result = len(p) * 20
		else:  # common anscestors
			result = len(ip) * 20
			result -= len(p) - len(ip)

		return max(0, result)

	@classmethod
	def get_ntiid_path(cls, item):
		result = ()
		if ISearchHit.providedBy(item):
			result = get_ntiid_path(item.Query.location)
		elif isinstance(item, six.string_types) and item and \
			 not ntiids.is_ntiid_of_types(item, cls.IGNORED_TYPES):
			result = get_ntiid_path(item)
		return result

	@classmethod
	def get_containerId(cls, item):
		result = None
		if ISearchHit.providedBy(item):
			result = item.ContainerId
		return result

	@Lazy
	def query(self):
		return self.results.query

	def compare(self, a, b):
		# compare location
		if self.query.origin != ntiids.ROOT:
			location_path = self.get_ntiid_path(a)
			a_path = self.get_ntiid_path(self.get_containerId(a))
			b_path = self.get_ntiid_path(self.get_containerId(b))
			a_score_path = self.score_path(location_path, a_path)
			b_score_path = self.score_path(location_path, b_path)
			result = cmp(b_score_path, a_score_path)
		else:
			result = 0

		# compare types.
		if result == 0:
			result = self.compare_type(a, b)

		# compare scores. Score comparation at the moment only make sense within
		# the same types  when we go to a unified index this we no longer need to
		# compare the types
		return self.compare_score(a, b) if result == 0 else result

@interface.implementer(ISearchHitComparatorFactory)
class _RelevanceSearchHitComparatorFactory(object):

	def __call__(self, results=None):
		return _RelevanceSearchHitComparator(results)
