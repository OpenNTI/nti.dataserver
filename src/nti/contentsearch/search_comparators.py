#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines search/index hit comparators.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import interface

import repoze.lru

from nti.ntiids import ntiids

from . import common
from . import content_utils
from . import interfaces as search_interfaces

class _CallableComparator(object):

	def __call__(self, a, b):
		return self.compare(a, b)

@interface.implementer(search_interfaces.ISearchHitComparator)
class _ScoreSearchHitComparator(_CallableComparator):

	@classmethod
	def get_score(cls, item):
		result = None
		if search_interfaces.ISearchHit.providedBy(item):
			result = item.Score
		return result or 1.0

	@classmethod
	def compare_score(cls, a, b):
		a_score = cls.get_score(a)
		b_score = cls.get_score(b)
		result = cmp(b_score, a_score)
		return result

	@classmethod
	def get_type_name(cls, item):
		if search_interfaces.ISearchHit.providedBy(item):
			result = item.Type
		else:
			result = u''
		return result or u''

	@classmethod
	def compare(cls, a, b):
		return cls.compare_score(a, b)

@interface.implementer(search_interfaces.ISearchHitComparator)
class _LastModifiedSearchHitComparator(_CallableComparator):

	@classmethod
	def get_lm(cls, item):
		if 	search_interfaces.ISearchHit.providedBy(item) or \
			hasattr(item, 'lastModified'):
			result = item.lastModified
		else:
			result = 0
		return result

	@classmethod
	def compare_lm(cls, a, b):
		a_lm = cls.get_lm(a)
		b_lm = cls.get_lm(b)
		result = cmp(a_lm, b_lm)
		return result

	@classmethod
	def compare(cls, a, b):
		return cls.compare_lm(a, b)

@interface.implementer(search_interfaces.ISearchHitComparator)
class _TypeSearchHitComparator(_ScoreSearchHitComparator,
							   _LastModifiedSearchHitComparator):

	@classmethod
	def compare_type(cls, a, b):
		a_order = common.get_sort_order(cls.get_type_name(a))
		b_order = common.get_sort_order(cls.get_type_name(b))
		result = cmp(a_order, b_order)
		return result

	@classmethod
	def compare(cls, a, b):
		result = cls.compare_type(a, b)
		if result == 0:
			result = cls.compare_lm(a, b)
		if result == 0:
			result = cls.compare_score(a, b)
		return result

@interface.implementer(search_interfaces.ISearchHitComparator)
class _CreatorSearchHitComparator(_ScoreSearchHitComparator,
							  	  _LastModifiedSearchHitComparator):

	@classmethod
	def compare_creator(cls, a, b):
		a_creator = a.Creator
		b_creator = b.Creator
		result = cmp(a_creator.lower(), b_creator.lower())
		return result

	@classmethod
	def compare(cls, a, b):
		result = cls.compare_creator(a, b)
		if result == 0:
			result = cls.compare_lm(b, a)  # more recent first
		if result == 0:
			result = cls.compare_score(a, b)
		return result

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
	result = content_utils.get_ntiid_path(item)
	return result

@interface.implementer(search_interfaces.ISearchHitComparator)
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
		if search_interfaces.ISearchHit.providedBy(item):
			result = get_ntiid_path(item.Query.location)
		elif isinstance(item, six.string_types) and item and \
			 not ntiids.is_ntiid_of_type(item, cls.IGNORED_TYPES):
			result = get_ntiid_path(item)
		return result

	@classmethod
	def get_containerId(cls, item):
		result = None
		if search_interfaces.ISearchHit.providedBy(item):
			result = item.ContainerId
		return result

	@classmethod
	def compare(cls, a, b):
		# compare location
		location_path = cls.get_ntiid_path(a)
		a_path = cls.get_ntiid_path(cls.get_containerId(a))
		b_path = cls.get_ntiid_path(cls.get_containerId(b))
		a_score_path = cls.score_path(location_path, a_path)
		b_score_path = cls.score_path(location_path, b_path)
		result = cmp(b_score_path, a_score_path)

		# compare types.
		if result == 0:
			result = cls.compare_type(a, b)

		# compare scores. Score comparation at the moment only make sense within
		# the same types  when we go to a unified index this we no longer need to
		# compare the types
		result = cls.compare_score(a, b) if result == 0 else result
		return result
