#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
... $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator

from .search_highlights import empty_hi_marker
from .search_highlights import word_fragments_highlight

from .interfaces import ISearchHit
from .interfaces import ISearchQuery
from .interfaces import INoteSearchHit
from .interfaces import IPostSearchHit
from .interfaces import ISearchResults
from .interfaces import IForumSearchHit
from .interfaces import ISuggestResults
from .interfaces import ISearchHitMetaData
from .interfaces import IRedactionSearchHit
from .interfaces import IWhooshNTICardSearchHit

from .constants import SNIPPET
from .constants import FRAGMENTS, TOTAL_FRAGMENTS, FIELD, ITEMS, SUGGESTIONS, HITS
from .constants import QUERY, HIT_COUNT, PHRASE_SEARCH, CREATED_TIME, SEARCH_QUERY

from .constants import tags_, content_, title_
from .constants import replacementContent_, redactionExplanation_

def _word_fragments_highlight(query=None, text=None):
	query = ISearchQuery(query, None)
	if query and text:
		surround = query.surround or 50
		maxchars = query.maxchars or 300
		result = word_fragments_highlight(	query, text,
											maxchars=maxchars,
											surround=surround,
											lang=query.language)
	else:
		result = empty_hi_marker
	return result

@component.adapter(ISearchHit)
@interface.implementer(IExternalObjectDecorator)
class _SearchHitHighlightDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		query = original.Query
		external.pop(CREATED_TIME, None)
		if query.applyHighlights:
			self.apply(query, original, external)

	def apply(self, query, hit, external):
		content_hi = None
		for field, text in self.sources(query, hit, external):
			hi = _word_fragments_highlight(query, text)
			content_hi = hi if field == content_ else content_hi
			if hi.match_count > 0:
				external[FIELD] = field
				self.set_snippet(hi, external)
				return

		if content_hi is not None:
			external[FIELD] = content_
			self.set_snippet(content_hi, external)

	def sources(self, query, hit, external):
		return ((content_, external.get(SNIPPET)),)
			
	def hilight_text(self, query, text):
		hi = _word_fragments_highlight(query, text)
		return hi

	def set_snippet(self, hi, external):
		external[SNIPPET] = hi.snippet
		if hi.fragments:
			external[FRAGMENTS] = toExternalObject(hi.fragments)
			external[TOTAL_FRAGMENTS] = hi.total_fragments

SearchHitHighlightDecorator = _SearchHitHighlightDecorator  # export

@component.adapter(INoteSearchHit)
@interface.implementer(IExternalObjectDecorator)
class _NoteSearchHitHighlightDecorator(_SearchHitHighlightDecorator):

	def sources(self, query, hit, external):
		return ((content_, external.get(SNIPPET)), (title_, hit.Title))

@component.adapter(IRedactionSearchHit)
@interface.implementer(IExternalObjectDecorator)
class _RedactionSearchHitHighlightDecorator(_SearchHitHighlightDecorator):

	def sources(self, query, hit, external):
		return ((content_, external.get(SNIPPET)),
				(replacementContent_, hit.ReplacementContent),
				(redactionExplanation_, hit.RedactionExplanation))

@component.adapter(IPostSearchHit)
@interface.implementer(IExternalObjectDecorator)
class _PostSearchHitHighlightDecorator(_SearchHitHighlightDecorator):

	def sources(self, query, hit, external):
		return ((content_, external.get(SNIPPET)),
				(title_, hit.Title),
				(tags_, hit.Tags))

@component.adapter(IForumSearchHit)
@interface.implementer(IExternalObjectDecorator)
class _ForumSearchHitHighlightDecorator(_SearchHitHighlightDecorator):

	def sources(self, query, hit, external):
		return ((title_, hit.Title), (content_, external.get(SNIPPET)))

@component.adapter(IWhooshNTICardSearchHit)
@interface.implementer(IExternalObjectDecorator)
class _NTICardSearchHitHighlightDecorator(_SearchHitHighlightDecorator):

	def sources(self, query, hit, external):
		return ((content_, external.get(SNIPPET)), (title_, hit.Title))

@interface.implementer(IExternalObjectDecorator)
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

@component.adapter(ISearchResults)
class _SearchResultsDecorator(_ResultsDecorator):
	pass

@component.adapter(ISuggestResults)
class _SuggestResultsDecorator(_ResultsDecorator):

	def decorateExternalObject(self, original, external):
		external[ITEMS] = external.pop(SUGGESTIONS, [])
		self.decorateCommon(original, external)

@component.adapter(ISearchHitMetaData)
class _SearchHitMetaDataDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		external.pop(StandardExternalFields.CREATED_TIME, None)
