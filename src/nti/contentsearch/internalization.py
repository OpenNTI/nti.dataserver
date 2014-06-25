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

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import InterfaceObjectIO

from . import interfaces as search_interfaces

from .constants import (ITEMS, HITS, SUGGESTIONS, QUERY, SEARCH_QUERY)

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

@interface.implementer(ext_interfaces.IInternalObjectUpdater)
@component.adapter(search_interfaces.ISearchQuery)
class _QueryObjectUpdater(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		_prune_readonly(parsed, search_interfaces.ISearchQuery)
		result = InterfaceObjectIO(
					self.obj,
					search_interfaces.ISearchQuery).updateFromExternalObject(parsed)
		return result

@interface.implementer(ext_interfaces.IInternalObjectUpdater)
@component.adapter(search_interfaces.ISearchHitMetaData)
class _SearchHitMetaDataUpdater(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		_prune_readonly(parsed, search_interfaces.ISearchHitMetaData)
		result = InterfaceObjectIO(
					self.obj,
					search_interfaces.ISearchHitMetaData).updateFromExternalObject(parsed)
		return result

def _transform_query(parsed):  # legacy query spec
	if SEARCH_QUERY in parsed:
		parsed[QUERY] = parsed[SEARCH_QUERY]
	elif QUERY in parsed and isinstance(parsed[QUERY], six.string_types):
		query = search_interfaces.ISearchQuery(parsed[QUERY])
		parsed[QUERY] = query

@interface.implementer(ext_interfaces.IInternalObjectUpdater)
class _SearchResultsUpdater(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		if ITEMS in parsed:
			parsed[HITS] = parsed[ITEMS]
			del parsed[ITEMS]

		if search_interfaces.ISuggestAndSearchResults.providedBy(self.obj):
			iface = search_interfaces.ISuggestAndSearchResults
		else:
			iface = search_interfaces.ISearchResults

		_transform_query(parsed)
		result = InterfaceObjectIO(self.obj, iface).updateFromExternalObject(parsed)

		# make sure we restore the query object to the hits
		for hit in self.obj._raw_hits():
			hit.Query = self.obj.Query

		return result

@interface.implementer(ext_interfaces.IInternalObjectUpdater)
@component.adapter(search_interfaces.ISuggestResults)
class _SuggestResultsUpdater(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		if ITEMS in parsed:
			parsed[SUGGESTIONS] = parsed[ITEMS]
			del parsed[ITEMS]

		_transform_query(parsed)
		result = InterfaceObjectIO(
					self.obj,
					search_interfaces.ISuggestResults).updateFromExternalObject(parsed)
		return result
