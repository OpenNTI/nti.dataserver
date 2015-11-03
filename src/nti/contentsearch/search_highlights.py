#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search highlight functionality

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
from heapq import nlargest

from zope import component
from zope import interface

import repoze.lru

from whoosh.analysis import RegexTokenizer
from whoosh.analysis import CompositeAnalyzer

from whoosh.highlight import FIRST
from whoosh.highlight import NullFormatter
from whoosh.highlight import ContextFragmenter
from whoosh.highlight import BasicFragmentScorer

from nti.contentfragments.interfaces import IPunctuationMarkPatternPlus
from nti.contentfragments.interfaces import IPunctuationMarkExpressionPlus

from nti.contentprocessing import tokenize_content
from nti.contentprocessing.interfaces import IWordTokenizerExpression

from .search_fragments import Range
from .search_fragments import create_from_terms
from .search_fragments import create_from_whoosh_fragment

from .interfaces import ISearchQuery
from .interfaces import IWhooshAnalyzer

null_formatter = NullFormatter()
basic_fragment_scorer = BasicFragmentScorer()

@interface.implementer(IWhooshAnalyzer)
def create_default_analyzer(lang='en'):
	expression = component.getUtility(IWordTokenizerExpression, name=lang)
	analyzers = [RegexTokenizer(expression=expression, gaps=False)]
	return CompositeAnalyzer(*analyzers)

def retokenize(text, lang='en'):
	analyzer = component.getUtility(IWhooshAnalyzer, name=lang)
	tokens = analyzer(text, chars=True, mode="query", removestops=False)
	return tokens

@repoze.lru.lru_cache(5)
def create_fragmenter(maxchars=300, surround=50):
	result = ContextFragmenter(maxchars=maxchars, surround=surround)
	return result

def get_query_terms(query, lang='en'):
	result = tokenize_content(query.term.lower(), lang)
	return result

class HighlightInfo(object):

	__slots__ = ('snippet', 'fragments', 'total_fragments')

	def __init__(self, snippet=None, fragments=(), total_fragments=0):
		self.fragments = fragments or ()
		self.total_fragments = total_fragments
		self.snippet = unicode(snippet) if snippet else u''

	@property
	def match_count(self):
		count = 0
		for sf in self.fragments:
			count += len(sf)
		return count
	matchCount = match_count

	@property
	def fragment_count(self):
		return self.total_fragments
	fragmentCount = fragment_count

	@property
	def search_fragments(self):
		return self.fragments
	searchFragments = search_fragments

empty_hi_marker = HighlightInfo()

def prune_phrase_terms_fragments(termset, original_snippet, original_fragments,
								 punkt_expression):
	snippets = []
	fragments = []
	t_len = len(termset)
	if t_len == 1:
		return original_snippet, original_fragments

	# create a pattern for the phrase terms
	termset = list(termset) if not isinstance(termset, (tuple, list)) else termset
	pattern = [termset[0]]
	for i in range(1, len(termset)):
		pattern.append(punkt_expression)
		pattern.append('+')
		pattern.append(termset[i])
	pattern = ''.join(pattern)
	pattern = re.compile(pattern, re.I | re.U)

	for fragment in original_fragments:
		matches = fragment.matches
		matched_len = len(matches)
		if matched_len < t_len:
			continue

		matched = re.search(pattern, fragment.text)
		if matched:
			fragment.matches = [Range(matched.start(), matched.end())]
			fragments.append(fragment)
			snippets.append(fragment.text)

	fragments = original_fragments if not fragments else fragments
	snippet = '...'.join(snippets) if snippets else original_snippet
	return snippet, fragments

def get_context_fragments(fragment, termset, query, maxchars, surround, punkt_pattern):
	text = fragment.text
	if not fragment.matches:
		return [fragment], text

	count = 0
	snippet = []
	fragments = []
	for m in fragment.matches:
		start = m.start
		end = m.end

		st = max(0, start - surround)
		if st == 0:
			start = 0
		else:
			for idx in range(st, start):
				if punkt_pattern.match(text[idx]):
					start = idx + 1
					break

		_len = len(text)
		ed = min(_len, end + surround)
		if ed == _len:
			end = _len
		else:
			for idx in range(-ed, -end):
				if punkt_pattern.match(text[-idx]):
					end = -idx
					break

		slc = text[start:end]
		if len(slc) == len(text):  # all the text selected
			return [fragment], text
		snippet.append(slc)

		# keep track of # chars
		count += len(slc)

		# create fragment
		sf = create_from_terms(slc, termset, query.IsPhraseSearch, punkt_pattern)
		fragments.append(sf)
		if count > maxchars:
			break

	snippet = '...'.join(snippet)
	return fragments, snippet

def top_fragments(whoosh_fragments, scorer, count=5, order=FIRST, minscore=1):
	scored_fragments = [(scorer(f), f) for f in whoosh_fragments]
	total_fragments = len(scored_fragments)
	if count:
		scored_fragments = nlargest(count, scored_fragments)

	best_fragments = [sf for score, sf in scored_fragments if score > minscore]
	best_fragments.sort(key=order)
	return best_fragments, total_fragments

def _no_hit_match(sf, maxchars=300, tokens=()):
	text = sf.text
	if len(text) > maxchars:
		tkn = None
		for t in tokens:
			if t.endchar >= maxchars:
				break
			tkn = t
		sf.text = text[:t.endchar] + '...' if tkn else u''
	return sf

def _set_matched_filter(tokens, termset):
	for t in tokens:
		t.matched = t.text in termset
		yield t

def word_fragments_highlight(query, text, maxchars=300, surround=50, top=5,
							 order=FIRST, lang='en'):
	# get lang. punkt char regex patter
	punkt_pattern = component.getUtility(IPunctuationMarkPatternPlus, name=lang)

	# get query terms
	text = unicode(text)
	query = ISearchQuery(query)
	termset = get_query_terms(query)

	# prepare fragmenter
	formatter = null_formatter  #  highlight.UppercaseFormatter()
	scorer = basic_fragment_scorer
	fragmenter = create_fragmenter(maxchars, surround)

	# sadly we need to retokenize to find term matches
	# user lowercase to match query terms
	tokens = retokenize(text.lower(), lang)

	# compute whoosh fragments
	tokens = _set_matched_filter(tokens, termset)
	whoosh_fragments = fragmenter.fragment_tokens(text, tokens)
	whoosh_fragments, total_fragments = \
							top_fragments(whoosh_fragments, scorer, top, order)

	if whoosh_fragments:
		fragments = []
		for f in whoosh_fragments:
			sf = create_from_whoosh_fragment(f, termset, punkt_pattern)
			fragments.append(sf)
		snippet = formatter(text, whoosh_fragments)
	else:
		sf = create_from_terms(text, termset, query.IsPhraseSearch, punkt_pattern)
		frags, snippet = get_context_fragments(sf, termset, query,
											   maxchars=maxchars,
											   surround=surround,
											   punkt_pattern=punkt_pattern)

		if len(frags) == 1 and not frags[0].matches:
			# At this point we could not find a match then,
			# it's easier to tokenize again rather than to copy the tokens.
			# Rememer The analyzer returns an generator
			tokens = retokenize(text, lang)  # use original text
			sf = _no_hit_match(sf, maxchars, tokens)
			snippet = sf.text
			total_fragments = 1
			fragments = [sf]
		else:
			fragments = frags
			total_fragments = len(frags)

	if query.IsPhraseSearch:
		punkt_exp = component.getUtility(IPunctuationMarkExpressionPlus,name=lang)
		snippet, fragments = \
			prune_phrase_terms_fragments(termset, snippet, fragments, punkt_exp)

	result = HighlightInfo(snippet, fragments, total_fragments)
	return result
