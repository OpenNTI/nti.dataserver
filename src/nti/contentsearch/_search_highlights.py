from __future__ import print_function, unicode_literals

import re
from collections import namedtuple

from zope import schema
from zope import component
from zope import interface

from whoosh import analysis
from whoosh import highlight

from nti.externalization import interfaces as ext_interfaces

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.common import default_word_tokenizer_expression

import logging
logger = logging.getLogger( __name__ )

WORD_HIGHLIGHT  = "WordHighlight"
WHOOSH_HIGHLIGHT = "WhooshHighlight"

_default_analyzer = None
_default_expression = default_word_tokenizer_expression #"\w+([-']\w+)*"
_default_pattern = re.compile(_default_expression, re.I)

def _get_terms(query, pattern=_default_pattern):
	pos = 0
	terms = []
	query = re.sub('[*?]','', query)
	m = pattern.search(query, pos)
	while m is not None:
		pos = m.end()
		term = query[m.start():pos]
		terms.append(term.lower())
		m = pattern.search(query, pos)
	return tuple(terms)

def _get_query_terms(query, pattern=_default_pattern):
	result = _get_terms(query.term, _default_pattern)
	if not query.is_phrase_search:
		result = frozenset(result)
	return result

def _get_default_analyzer():
	global _default_analyzer
	if _default_analyzer is None:
		sw_util = component.queryUtility(search_interfaces.IStopWords) 
		stoplist = sw_util.stopwords() if sw_util else ()
		analyzers = [analysis.RegexTokenizer(expression=_default_expression, gaps=False),
					 analysis.LowercaseFilter(),
					 analysis.StopFilter(stoplist=stoplist) ]
		_default_analyzer = analysis.CompositeAnalyzer(*analyzers)
	return _default_analyzer

def _set_matched_filter(tokens, termset):
	for t in tokens:
		t.matched = t.text in termset
		yield t
	
_re_char = r"[ \? | ( | \" | \` | { | \[ | : | ; | & | \# | \* | @ | \) | } | \] | \- | , | \. | ! | \s]"
_char_tester = re.compile(_re_char)

def _is_word_start(idx, text):
	result = idx == 0 or _char_tester.match(text[idx-1])
	return result

def _is_word_end(idx, text):
	result = idx == len(text) or _char_tester.match(text[idx])
	return result
		
def _match_text(self, text):
	return self.text.lower() == text.lower()

def _range_equals(self, other):
	result = False
	if isinstance(other, (list, tuple, _Range)) and len(other) >=2:
		result = self.start == other[0] and self.end == other[1]
	return result
	
_Range = namedtuple('_Range', 'start end text')
_Range.match = _match_text
_Range.__eq__ = _range_equals
	
class ISearchFragment(ext_interfaces.IExternalObject):
	text = schema.TextLine(title="fragment text", required=True)
	matches = schema.Iterable("Iterable with pair tuples where a match occurs", required=True)
	
@interface.implementer(ISearchFragment)
class _SearchFragment(object):
	text = None
	matches = ()

	def __len__(self):
		return len(self.matches)
	
	def __repr__(self):
		return "<%s %r %r>" % (self.__class__.__name__, self.text, self.matches)
	
	def toExternalObject(self):
		ranges = [(m.start, m.end) for m in self.matches]
		result = {'text': self.text or u'',
				  'matches': ranges}
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
	def _match_terms(cls, fragment, termset, check_start_word=False, check_end_word=False):
		matches = []
		for term in termset:
			idx = 0
			_len = len(term)
			idx = fragment.find(term, idx)
			while idx >=0:
				endidx = idx + _len
				if  (not check_start_word or _is_word_start(idx, fragment) ) and \
					(not check_end_word or _is_word_end(endidx, fragment)):
					mrange = _Range(idx, endidx, term)
					matches.append(mrange)
				idx = fragment.find(term, endidx)
		matches = cls._clean_ranges(matches)
		return matches
	
	@classmethod
	def create_from_whoosh_fragment(cls, wf, termset):
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
			m = cls._match_terms(fragment.lower(), termset, True, False)
			matches.extend(m)
			matches = sorted(matches, key=lambda ra: ra.start)
			
		result = _SearchFragment()
		result.text = fragment
		result.matches = matches if matches else ()
		return result
	
	@classmethod
	def create_from_terms(cls, text, termset, check_word=False):
		fragment = text
		matches = cls._match_terms(fragment.lower(), termset, check_word, check_word)
		matches = sorted(matches, key=lambda ra: ra.start)
		result = _SearchFragment()
		result.text = fragment
		result.matches = matches if matches else ()
		return result

def _prune_fragments(termset, original_snippet, original_fragments):
	snippets = []
	fragments = []
	_len = len(termset)
	if _len == 1:
		return original_snippet, original_fragments
	
	# create a pattern for the phrase terms
	termset = list(termset) if not isinstance(termset, list) else termset
	pattern = [termset[0]]
	for i in range(1, len(termset)):
		pattern.append(_re_char)
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

def _search_fragment_snippet(text, fragment, surround=50):
	if not fragment.matches:
		return text
	
	start = fragment.matches[0].start
	end = fragment.matches[-1].end

	st = max(0, start - surround)
	if st == 0:
		start = 0
	else:
		for idx in range(st, start):
			if _char_tester.match(text[idx]):
				start = idx + 1
				break
	
	_len = len(text)
	ed = min(_len, end + surround)
	if ed == _len:
		end = _len
	else:
		for idx in range(-ed, -end):
			if _char_tester.match(text[-idx]):
				end = -idx
				break
		
	snippet = text[start:end]
	return snippet

def word_fragments_highlight(query, text, maxchars=300, surround=50, top=3, analyzer=None, order=highlight.FIRST):

	# get query terms
	text = unicode(text)	
	query = search_interfaces.ISearchQuery(query)
	termset = _get_query_terms(query)
	
	# prepare fragmenter
	scorer = highlight.BasicFragmentScorer()
	analyzer = analyzer or _get_default_analyzer()
	formatter = highlight.NullFormatter() #  highlight.UppercaseFormatter()
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
	
	# sadly we need to retokenize to find term matches
	tokens = analyzer(text, chars=True, mode="query", removestops=False)
	
	# compute whoosh fragments
	tokens = _set_matched_filter(tokens, termset)
	fragments = fragmenter.fragment_tokens(text, tokens)
	fragments = highlight.top_fragments(fragments, top, scorer, order)
	
	if fragments:
		search_fragments = []
		for f in fragments:
			sf = _SearchFragment.create_from_whoosh_fragment(f, termset)
			search_fragments.append(sf)	
		snippet = formatter(text, fragments)
	else:
		sf = _SearchFragment.create_from_terms(text, termset, query.is_phrase_search)
		snippet = _search_fragment_snippet(text, sf)
		search_fragments = [sf]
		
	if query.is_phrase_search:
		snippet, search_fragments =  _prune_fragments(termset, snippet, search_fragments)
	
	return snippet, search_fragments

def substring_fragments_highlight(query, text):
	snippet = text
	termset = _get_terms(query)
	search_fragments = [_SearchFragment.search_fragments(text, termset)]
	return snippet, search_fragments

def word_content_highlight(query, text, maxchars=300, surround=50, top=3, analyzer=None):
	terms = _get_terms(query)
	analyzer = analyzer or _get_default_analyzer()
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
	formatter = highlight.NullFormatter() # highlight.UppercaseFormatter()
	result = highlight.highlight(text, terms, analyzer, fragmenter, formatter, top=top)
	return result

