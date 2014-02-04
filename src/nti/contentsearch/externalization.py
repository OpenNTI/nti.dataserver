# -*- coding: utf-8 -*-
"""
Search externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from z3c.batching.batch import Batch

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import InterfaceObjectIO
from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.autopackage import AutoPackageSearchingScopedInterfaceObjectIO

from . import search_hits
from . import interfaces as search_interfaces

from .constants import (LAST_MODIFIED, QUERY, HIT_COUNT, ITEMS,
					 	SUGGESTIONS, PHRASE_SEARCH, HIT_META_DATA)

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(search_interfaces.ISearchHit)
class _SearchHitMetaDataExternal(InterfaceObjectIO):

	_excluded_out_ivars_ = {'Query'} | InterfaceObjectIO._excluded_out_ivars_
	_ext_iface_upper_bound = search_interfaces.ISearchHit

# search metadata

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(search_interfaces.IIndexHitMetaData)
class _IndexHitMetaDataExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = search_interfaces.IIndexHitMetaData

# search results

@interface.implementer(ext_interfaces.IExternalObject)
class _BaseSearchResultsExternalizer(object):

	def __init__(self, results):
		self.results = results

	@property
	def query(self):
		return self.results.query

	def toExternalObject(self):
		eo = LocatedExternalDict()
		eo[QUERY] = self.query.term
		return eo

@component.adapter(search_interfaces.ISearchResults)
class _SearchResultsExternalizer(_BaseSearchResultsExternalizer):

	def __init__(self, results):
		super(_SearchResultsExternalizer, self).__init__(results)
		self.seen = set()

	@property
	def is_batching(self):
		return self.query.is_batching

	@property
	def batchSize(self):
		return self.query.batchSize

	@property
	def batchStart(self):
		return self.query.batchStart

	@property
	def hits(self):
		sortOn = self.query.sortOn
		if sortOn and not self.results.sorted:
			self.results.sort(sortOn)

		if self.is_batching:
			if self.batchStart < len(self.results):
				return Batch(self.results.hits, start=self.batchStart,
							 size=self.batchSize)
			else:
				return ()
		else:
			return self.results.hits

	def toExternalObject(self):
		result = super(_SearchResultsExternalizer, self).toExternalObject()
		result[ITEMS] = items = []
		result[PHRASE_SEARCH] = self.query.is_phrase_search

		# process hits
		count = 0
		lastModified = 0
		limit = self.query.limit

		for hit in self.hits:

			item = hit.obj if hit is not None else None
			if item is None:
				continue

			score = hit.score
			query = hit.query

			hit = search_hits.get_search_hit(item, score, query)
			if hit.OID in self.seen:
				continue

			self.seen.add(hit.OID)
			lastModified = max(lastModified, hit.lastModified)

			external = toExternalObject(hit)
			items.append(external)

			count += 1
			if count >= limit:
				break

		result[HIT_COUNT] = len(items)
		result[LAST_MODIFIED] = lastModified
		result[HIT_META_DATA] = toExternalObject(self.results.metadata)

		# set for IUGDExternalCollection
		result.lastModified = lastModified
		result.mimeType = self.results.mimeType

		return result

@component.adapter(search_interfaces.ISuggestResults)
class _SuggestResultsExternalizer(_BaseSearchResultsExternalizer):

	@property
	def suggestions(self):
		return self.results.suggestions

	def toExternalObject(self):
		result = super(_SuggestResultsExternalizer, self).toExternalObject()
		result[ITEMS] = items = [item for item in self.suggestions if item is not None]
		result[SUGGESTIONS] = items
		result[HIT_COUNT] = len(items)
		result[LAST_MODIFIED] = 0
		return result

@component.adapter(search_interfaces.ISuggestAndSearchResults)
class _SuggestAndSearchResultsExternalizer(_SearchResultsExternalizer,
										   _SuggestResultsExternalizer):

	def toExternalObject(self):
		result = _SearchResultsExternalizer.toExternalObject(self)
		result[SUGGESTIONS] = self.suggestions
		return result

@interface.implementer(ext_interfaces.IInternalObjectIO)
class _IndexHitInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):
	
	_excluded_out_ivars_ = {'Query'} | AutoPackageSearchingScopedInterfaceObjectIO._excluded_out_ivars_
	_excluded_in_ivars_ = {'Query'} | AutoPackageSearchingScopedInterfaceObjectIO._excluded_in_ivars_

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces(cls, search_interfaces):
		return (search_interfaces.IIndexHit,)

	@classmethod
	def _ap_enumerate_module_names(cls):
		return ('search_results',)

_IndexHitInternalObjectIO.__class_init__()

@interface.implementer(ext_interfaces.IInternalObjectIO)
class _SearchHitInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):

	_excluded_out_ivars_ = {'Query'} | AutoPackageSearchingScopedInterfaceObjectIO._excluded_out_ivars_
	_excluded_in_ivars_ = {'Query'} | AutoPackageSearchingScopedInterfaceObjectIO._excluded_in_ivars_

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces(cls, search_interfaces):
		return (search_interfaces.ISearchHit,)

	@classmethod
	def _ap_enumerate_module_names(cls):
		return ('search_hits',)

_SearchHitInternalObjectIO.__class_init__()
