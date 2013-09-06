# -*- coding: utf-8 -*-
"""
Search externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component
from zope import interface

from z3c.batching.batch import Batch

from pyramid.threadlocal import get_current_request

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator
from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.autopackage import AutoPackageSearchingScopedInterfaceObjectIO

from nti.dataserver.links import Link

from ._search_hits import get_search_hit
from . import interfaces as search_interfaces
from ._search_highlights import HighlightInfo
from ._search_highlights import word_fragments_highlight

from .constants import (tags_, content_, title_, replacementContent_, redactionExplanation_)
from .constants import (LAST_MODIFIED, SNIPPET, QUERY, HIT_COUNT, ITEMS, TOTAL_HIT_COUNT,
					 	SUGGESTIONS, FRAGMENTS, PHRASE_SEARCH, TOTAL_FRAGMENTS, FIELD, TYPE_COUNT,
					 	HIT_META_DATA)

# highlight decorators

def _word_fragments_highlight(query=None, text=None):
	query = search_interfaces.ISearchQuery(query, None)
	if query and text:
		result = word_fragments_highlight(query, text, query.language)
	else:
		result = HighlightInfo()
	return result

# search hits

@component.adapter(search_interfaces.ISearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _SearchHitHighlightDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		query = original.query
		text = external.get(SNIPPET, None)
		hi = self.hilight_text(query, text)
		self.set_snippet(hi, external)

	def hilight_text(self, query, text):
		hi = _word_fragments_highlight(query, text)
		return hi

	def set_snippet(self, hi, external):
		external[SNIPPET] = hi.snippet
		if hi.fragments:
			external[FRAGMENTS] = toExternalObject(hi.fragments)
			external[TOTAL_FRAGMENTS] = hi.total_fragments

class _MultipleFieldSearchHitHighlightDecorator(_SearchHitHighlightDecorator):

	def decorate_on_source_fields(self, hit, external, sources):
		query = hit.query
		content_hi = None
		for field, text in sources:
			hi = _word_fragments_highlight(query, text)
			content_hi = hi if not content_hi else content_hi
			if hi.match_count > 0:
				self.set_snippet(hi, external)
				external[FIELD] = field
				return

		if content_hi:
			external[FIELD] = field
			self.set_snippet(content_hi, external)

@component.adapter(search_interfaces.INoteSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _NoteSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):

	def decorateExternalObject(self, hit, external):
		t_sources = ((content_, external.get(SNIPPET)), (title_, hit.get_title()))
		self.decorate_on_source_fields(hit, external, t_sources)

@component.adapter(search_interfaces.IRedactionSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _RedactionSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):

	def decorateExternalObject(self, hit, external):
		t_sources = ((content_, external.get(SNIPPET, None)),
					(replacementContent_, hit.get_replacement_content()),
					(redactionExplanation_, hit.get_redaction_explanation()))
		self.decorate_on_source_fields(hit, external, t_sources)

@component.adapter(search_interfaces.IPostSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _PostSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):

	def decorateExternalObject(self, hit, external):
		t_sources = ((content_, external.get(SNIPPET, None)),
					(title_, hit.get_title()),
					(tags_, hit.get_tags()))
		self.decorate_on_source_fields(hit, external, t_sources)

@component.adapter(search_interfaces.IWhooshNTICardSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _NTICardSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):

	def decorateExternalObject(self, hit, external):
		t_sources = ((content_, external.get(SNIPPET)), (title_, hit.get_title()))
		self.decorate_on_source_fields(hit, external, t_sources)

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(search_interfaces.ISearchHit)
class _SearchHitExternalizer(object):

	__slots__ = ('hit',)

	def __init__(self, hit):
		self.hit = hit

	def toExternalObject(self):
		return self.hit

# search metadata

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(search_interfaces.IIndexHitMetaData)
class _IndexHitMetaDataExternalizer(object):

	__slots__ = ('data',)

	def __init__(self, data):
		self.data = data

	def toExternalObject(self):
		result = LocatedExternalDict()
		result[LAST_MODIFIED] = self.data.last_modified
		result[TOTAL_HIT_COUNT] = self.data.total_hit_count
		result[TYPE_COUNT] = {k.capitalize():v for k, v in self.data.type_count.items()}
		return result

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
				return Batch(self.results.hits, start=self.batchStart, size=self.batchSize)
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
		last_modified = 0
		limit = self.query.limit

		for hit in self.hits:

			item = hit.obj if hit is not None else None
			if item is None:
				continue

			score = hit.score
			query = hit.query

			hit = get_search_hit(item, score, query)
			if hit.oid in self.seen:
				continue

			self.seen.add(hit.oid)
			last_modified = max(last_modified, hit.last_modified)

			external = toExternalObject(hit)
			items.append(external)

			count += 1
			if count >= limit:
				break

		result[HIT_COUNT] = len(items)
		result[LAST_MODIFIED] = last_modified
		result[HIT_META_DATA] = toExternalObject(self.results.get_hit_meta_data())

		# set for IUGDExternalCollection
		result.lastModified = last_modified
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
class _SuggestAndSearchResultsExternalizer(_SearchResultsExternalizer, _SuggestResultsExternalizer):

	def toExternalObject(self):
		result = _SearchResultsExternalizer.toExternalObject(self)
		result[SUGGESTIONS] = self.suggestions
		return result

@component.adapter(search_interfaces.ISearchResults)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _SearchResultsLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		query = original.query
		if query.is_batching:
			request = get_current_request()
			if request is None: return

			# Insert links to the next and previous batch
			result_list = Batch(original.hits, query.batchStart, query.batchSize)
			next_batch, prev_batch = result_list.next, result_list.previous
			for batch, rel in ((next_batch, 'batch-next'), (prev_batch, 'batch-prev')):
				if batch is not None and batch != result_list:
					batch_params = request.params.copy()
					batch_params['batchStart'] = batch.start
					link_next_href = request.current_route_path(_query=sorted(batch_params.items()))
					link_next = Link(link_next_href, rel=rel)
					external.setdefault('Links', []).append(link_next)


@interface.implementer(ext_interfaces.IInternalObjectIO)
class _SearchInternalObjectIO(AutoPackageSearchingScopedInterfaceObjectIO):

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces(cls, search_interfaces):
		return (search_interfaces.IWhooshBookContent, search_interfaces.IWhooshVideoTranscriptContent,
				search_interfaces.IWhooshNTICardContent, search_interfaces.IIndexHit, search_interfaces.ISearchQuery)

	@classmethod
	def _ap_enumerate_module_names(cls):
		return ('_whoosh_index', '_search_results', '_search_query')

_SearchInternalObjectIO.__class_init__()

