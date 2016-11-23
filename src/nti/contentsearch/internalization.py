#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
search internalization

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import schema
from zope import interface
from zope import component

from nti.externalization.datastructures import InterfaceObjectIO
from nti.externalization.interfaces import IInternalObjectUpdater

from .interfaces import ISearchQuery
from .interfaces import ISearchResults
from .interfaces import ISuggestResults
from .interfaces import ISearchHitMetaData

from .constants import ITEMS, HITS, SUGGESTIONS, QUERY, SEARCH_QUERY

def _readonly(iface):
	result = set()
	for name in schema.getFieldNames(iface):
		if iface[name].readonly:
			result.add(name)
	return result

def _prune_readonly(parsed, iface):
	for name in _readonly(iface):
		if name in parsed:
			del parsed[name]

@interface.implementer(IInternalObjectUpdater)
@component.adapter(ISearchQuery)
class _QueryObjectUpdater(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		_prune_readonly(parsed, ISearchQuery)
		result = InterfaceObjectIO(self.obj, ISearchQuery).updateFromExternalObject(parsed)
		return result

@interface.implementer(IInternalObjectUpdater)
@component.adapter(ISearchHitMetaData)
class _SearchHitMetaDataUpdater(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		_prune_readonly(parsed, ISearchHitMetaData)
		result = InterfaceObjectIO(self.obj,
								   ISearchHitMetaData).updateFromExternalObject(parsed)
		return result

def _transform_query(parsed):  # legacy query spec
	if SEARCH_QUERY in parsed:
		parsed[QUERY] = parsed[SEARCH_QUERY]
	elif QUERY in parsed and isinstance(parsed[QUERY], six.string_types):
		query = ISearchQuery(parsed[QUERY])
		parsed[QUERY] = query

@interface.implementer(IInternalObjectUpdater)
class _SearchResultsUpdater(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		if ITEMS in parsed:
			parsed[HITS] = parsed[ITEMS]
			del parsed[ITEMS]

		_transform_query(parsed)
		result = InterfaceObjectIO(self.obj, ISearchResults).updateFromExternalObject(parsed)

		# make sure we restore the query object to the hits
		for hit in self.obj._raw_hits():
			hit.Query = self.obj.Query

		return result

@interface.implementer(IInternalObjectUpdater)
@component.adapter(ISuggestResults)
class _SuggestResultsUpdater(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		if ITEMS in parsed:
			parsed[SUGGESTIONS] = parsed[ITEMS]
			del parsed[ITEMS]

		_transform_query(parsed)
		result = InterfaceObjectIO(self.obj,
								   ISuggestResults).updateFromExternalObject(parsed)
		return result
