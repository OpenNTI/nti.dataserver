#!/usr/bin/env python
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

from pyramid.threadlocal import get_current_request

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator
from nti.externalization.externalization import toExternalObject

from nti.dataserver.links import Link

from . import search_highlights
from . import interfaces as search_interfaces

from .constants import (tags_, content_, title_, replacementContent_,
						redactionExplanation_)

from .constants import (FRAGMENTS, TOTAL_FRAGMENTS, FIELD, ITEMS, SUGGESTIONS, HITS,
						QUERY, HIT_COUNT, PHRASE_SEARCH, CREATED_TIME, SEARCH_QUERY)

SNIPPET = 'Snippet'

def _word_fragments_highlight(query=None, text=None):
	query = search_interfaces.ISearchQuery(query, None)
	if query and text:
		result = search_highlights.word_fragments_highlight(query, text,
															lang=query.language)
	else:
		result = search_highlights.empty_hi_marker
	return result

@component.adapter(search_interfaces.ISearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _SearchHitHighlightDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		query = original.Query
		external.pop(CREATED_TIME, None)
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
		query = hit.Query
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
		t_sources = ((content_, external.get(SNIPPET)), (title_, hit.Title))
		self.decorate_on_source_fields(hit, external, t_sources)

@component.adapter(search_interfaces.IRedactionSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _RedactionSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):

	def decorateExternalObject(self, hit, external):
		t_sources = ((content_, external.get(SNIPPET)),
					(replacementContent_, hit.ReplacementContent),
					(redactionExplanation_, hit.RedactionExplanation))
		self.decorate_on_source_fields(hit, external, t_sources)

@component.adapter(search_interfaces.IPostSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _PostSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):

	def decorateExternalObject(self, hit, external):
		t_sources = ((content_, external.get(SNIPPET)),
					 (title_, hit.Title),
					 (tags_, hit.Tags))
		self.decorate_on_source_fields(hit, external, t_sources)

@component.adapter(search_interfaces.IForumSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _ForumSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):

	def decorateExternalObject(self, hit, external):
		t_sources = ((title_, hit.Title), (content_, external.get(SNIPPET)))
		self.decorate_on_source_fields(hit, external, t_sources)

@component.adapter(search_interfaces.IWhooshNTICardSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _NTICardSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):

	def decorateExternalObject(self, hit, external):
		t_sources = ((content_, external.get(SNIPPET)), (title_, hit.Title))
		self.decorate_on_source_fields(hit, external, t_sources)

@component.adapter(search_interfaces.ISearchResults)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _SearchResultsLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		query = original.Query
		request = get_current_request()
		batch_hits = getattr(original, 'Batch', None)
		if request is None or not query.IsBatching or batch_hits is None:
			return

		next_batch, prev_batch = batch_hits.next, batch_hits.previous
		for batch, rel in ((next_batch, 'batch-next'), (prev_batch, 'batch-prev')):
			if batch is not None and batch != batch_hits:
				batch_params = request.params.copy()
				batch_params['batchStart'] = batch.start
				_query = sorted(batch_params.items())
				link_next_href = request.current_route_path(_query=_query)
				link_next = Link(link_next_href, rel=rel)
				external.setdefault('Links', []).append(link_next)
		# clean
		original.Batch = None

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _ResultsDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateCommon(self, original, external):
		external.pop(CREATED_TIME, None)
		external[SEARCH_QUERY] = external[QUERY]
		external[QUERY] = original.Query.term
		external[HIT_COUNT] = len(external[ITEMS])
		external[PHRASE_SEARCH] = original.Query.is_phrase_search

	def decorateExternalObject(self, original, external):
		external[ITEMS] = external.pop(HITS, [])
		self.decorateCommon(original, external)

@component.adapter(search_interfaces.ISearchResults)
class _SearchResultsDecorator(_ResultsDecorator):
	pass

@component.adapter(search_interfaces.ISuggestResults)
class _SuggestResultsDecorator(_ResultsDecorator):

	def decorateExternalObject(self, original, external):
		if not search_interfaces.ISuggestAndSearchResults.providedBy(original):
			external[ITEMS] = external.pop(SUGGESTIONS, [])
			self.decorateCommon(original, external)

@component.adapter(search_interfaces.ISearchHitMetaData)
class _SearchHitMetaDataDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		external.pop(ext_interfaces.StandardExternalFields.CREATED_TIME, None)
