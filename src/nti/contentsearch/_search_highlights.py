# -*- coding: utf-8 -*-
"""
Search highlight functionality

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
from heapq import nlargest

from zope import schema
from zope import component
from zope import interface

from whoosh import analysis
from whoosh import highlight

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import LocatedExternalDict

from nti.utils import schema as nti_schema

from nti.contentprocessing import split_content
from nti.contentprocessing import interfaces as cp_interfaces

from . import interfaces as search_interfaces

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

	@property
	def fragment_count(self):
		return self.total_fragments

	@property
	def search_fragments(self):
		return self.fragments

@interface.implementer(search_interfaces.IWhooshAnalyzer)
def _create_default_analyzer(lang='en'):
	sw_util = component.queryUtility(search_interfaces.IStopWords, name=lang)
	expression = component.getUtility(cp_interfaces.IWordTokenizerExpression, name=lang)
	stoplist = sw_util.stopwords() if sw_util else ()
	analyzers = [analysis.RegexTokenizer(expression=expression, gaps=False),
				 analysis.LowercaseFilter(),
				 analysis.StopFilter(stoplist=stoplist) ]
	return analysis.CompositeAnalyzer(*analyzers)

def _get_query_terms(query, lang='en'):
	result = split_content(query.term.lower(), lang)
	return result

def _is_word_start(idx, text, punkt_pattern):
	result = idx == 0 or punkt_pattern.match(text[idx - 1])
	return result

def _is_word_end(idx, text, punkt_pattern):
	result = idx == len(text) or punkt_pattern.match(text[idx])
	return result

class _Range(object):

	__slots__ = ('start', 'end', 'text')

	def __init__(self, start, end, text):
		self.end = end
		self.text = text
		self.start = start

	def __str__(self):
		return "{0}.{1}({2},{3},'{4}')".format(self.__class__.__module__, self.__class__.__name__,
											   self.start, self.end, self.text.encode('unicode_escape') if self.text else '')

	__repr__ = __str__

	def __eq__(self, other):
		try:
			return self is other or (self.start == other.start and self.end == other.end)
		except AttributeError:
			if isinstance(other, (list, tuple)):  # for testing (XXX: dubious)
				return len(other) >= 2 and self.start == other[0] and self.end == other[1]
			return NotImplemented

	def __hash__(self):
		return hash((self.start, self.end))

class ISearchFragment(ext_interfaces.IExternalObject):
	text = nti_schema.ValidTextLine(title="fragment text", required=True)
	matches = schema.Iterable("Iterable with pair tuples where a match occurs", required=True)

@interface.implementer(ISearchFragment)
class _SearchFragment(object):

	__slots__ = ('text', 'matches')

	def __init__(self, text=None, matches=()):
		self.text = text
		self.matches = matches

	def __len__(self):
		return len(self.matches)

	def __str__(self):
		return "<%s %r %r>" % (self.__class__.__name__, self.text, self.matches)

	__repr__ = __str__

	def toExternalObject(self):
		ranges = [(m.start, m.end) for m in self.matches]
		result = LocatedExternalDict()
		result['text'] = self.text or u''
		result['matches'] = ranges
		return result

	@classmethod
	def _is_range_subsumed(cls, refidx, v, ranges):
		for idx, t in enumerate(ranges):
			if idx != refidx:
				if v.start >= t.start and v.end <= t.end:
					return True
		return False

	@classmethod
	def _clean_ranges(cls, matches):
		result = []
		for idx, r in enumerate(matches):
			if not cls._is_range_subsumed(idx, r, matches):
				result.append(r)
		return result

	@classmethod
	def _match_terms(cls, fragment, termset, check_start_word, check_end_word, punkt_pattern):
		matches = []
		for term in termset:
			idx = 0
			_len = len(term)
			idx = fragment.find(term, idx)
			while idx >= 0:
				endidx = idx + _len
				if  (not check_start_word or _is_word_start(idx, fragment, punkt_pattern)) and \
					(not check_end_word or _is_word_end(endidx, fragment, punkt_pattern)):
					mrange = _Range(idx, endidx, term)
					matches.append(mrange)
				idx = fragment.find(term, endidx)
		matches = cls._clean_ranges(matches)
		return matches

	@classmethod
	def create_from_whoosh_fragment(cls, wf, termset, punkt_pattern):
		matches = []
		termset = set(termset)
		offset = wf.startchar
		for t in wf.matches:
			txt = t.text.lower()
			if txt in termset:
				termset.remove(txt)
			idx = t.startchar - offset
			endidx = t.endchar - offset
			mrange = _Range(idx, endidx, txt)
			matches.append(mrange)

		fragment = wf.text[wf.startchar:wf.endchar]
		if termset:
			m = cls._match_terms(fragment.lower(), termset, True, False, punkt_pattern)
			matches.extend(m)
			matches = sorted(matches, key=lambda ra: ra.start)

		result = _SearchFragment()
		result.text = fragment
		result.matches = matches if matches else ()
		return result

	@classmethod
	def create_from_terms(cls, text, termset, check_word, punkt_pattern):
		fragment = text
		matches = cls._match_terms(fragment.lower(), termset, check_word, check_word, punkt_pattern)
		matches = sorted(matches, key=lambda ra: ra.start)
		result = _SearchFragment()
		result.text = fragment
		result.matches = matches if matches else ()
		return result

def _prune_phrase_terms_fragments(termset, original_snippet, original_fragments, punkt_expression):
	snippets = []
	fragments = []
	_len = len(termset)
	if _len == 1:
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

	for sf in original_fragments:
		matches = sf.matches
		matched_len = len(matches)
		if matched_len < _len:
			continue

		matched = re.search(pattern, sf.text)
		if matched:
			sf.matches = [_Range(matched.start(), matched.end(), None)]
			fragments.append(sf)
			snippets.append(sf.text)

	fragments = original_fragments if not fragments else fragments
	snippet = '...'.join(snippets) if snippets else original_snippet
	return snippet, fragments

def _context_fragments(sf, termset, query, maxchars, surround, punkt_pattern):
	text = sf.text
	if not sf.matches:
		return [sf], text

	count = 0
	snippet = []
	fragments = []
	for m in sf.matches:
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

		s = text[start:end]
		snippet.append(s)
		# keep track of # chars
		count += len(s)
		# create fragment
		sf = _SearchFragment.create_from_terms(s, termset, query.is_phrase_search, punkt_pattern)
		fragments.append(sf)
		if count > maxchars:
			break

	snippet = '...'.join(snippet)
	return fragments, snippet

def _no_hit_match(sf, maxchars=300, tokens=()):
	text = sf.text
	if len(text) > maxchars:
		tkn = None
		for t in tokens:
			if t.endchar >= maxchars: break
			tkn = t
		sf.text = text[:t.endchar] + '...' if tkn else u''
	return sf

def _set_matched_filter(tokens, termset):
	for t in tokens:
		t.matched = t.text in termset
		yield t

def top_fragments(fragments, scorer, count=5, order=highlight.FIRST, minscore=1):
	scored_fragments = [(scorer(f), f) for f in fragments]
	total_fragments = len(scored_fragments)
	if count:
		scored_fragments = nlargest(count, scored_fragments)

	best_fragments = [sf for score, sf in scored_fragments if score > minscore]
	best_fragments.sort(key=order)
	return best_fragments, total_fragments

def word_fragments_highlight(query, text, maxchars=300, surround=50, top=5, order=highlight.FIRST, lang='en'):

	punkt_pattern = component.getUtility(cp_interfaces.IPunctuationCharPatternPlus, name=lang)

	# get query terms
	text = unicode(text)
	query = search_interfaces.ISearchQuery(query)
	termset = _get_query_terms(query)

	# prepare fragmenter
	# TODO: could we have a context scorer?
	scorer = highlight.BasicFragmentScorer()
	analyzer = component.getUtility(search_interfaces.IWhooshAnalyzer, name=lang)
	formatter = highlight.NullFormatter()  #  highlight.UppercaseFormatter()
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)

	# sadly we need to retokenize to find term matches
	tokens = analyzer(text, chars=True, mode="query", removestops=False)
	if len(text) > maxchars:
		copy_tokens = [t.copy() for t in tokens]
		tokens = copy_tokens
	else:
		copy_tokens = ()

	# compute whoosh fragments
	tokens = _set_matched_filter(tokens, termset)
	fragments = fragmenter.fragment_tokens(text, tokens)
	fragments, total_fragments = top_fragments(fragments, scorer, top, order)

	if fragments:
		del copy_tokens
		search_fragments = []
		for f in fragments:
			sf = _SearchFragment.create_from_whoosh_fragment(f, termset, punkt_pattern)
			search_fragments.append(sf)
		snippet = formatter(text, fragments)
	else:
		sf = _SearchFragment.create_from_terms(text, termset, query.is_phrase_search, punkt_pattern)
		frags, snippet = _context_fragments(sf, termset, query, maxchars=maxchars, surround=surround, punkt_pattern=punkt_pattern)
		if len(frags) == 1 and not frags[0].matches:
			sf = _no_hit_match(sf, maxchars, copy_tokens)
			snippet = sf.text
			total_fragments = 1
			search_fragments = [sf]
		else:
			del copy_tokens
			search_fragments = frags
			total_fragments = len(frags)

	if query.is_phrase_search:
		punkt_exp = component.getUtility(cp_interfaces.IPunctuationCharExpressionPlus, name=lang)
		snippet, search_fragments = _prune_phrase_terms_fragments(termset, snippet, search_fragments, punkt_exp)

	result = HighlightInfo(snippet, search_fragments, total_fragments)
	return result
