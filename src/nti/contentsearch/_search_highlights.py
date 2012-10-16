from __future__ import print_function, unicode_literals

import re
from collections import namedtuple
from collections import defaultdict

from zope import schema
from zope import component
from zope import interface
from ZODB import loglevels

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
		terms.append(term)
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
					 analysis.LowercaseFilter() ]
		if stoplist:
			analyzers.append(analysis.StopFilter(stoplist=stoplist))
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
	def create_from_whoosh_fragment(cls, wf):
		matches = []
		fragment = wf.text[wf.startchar:wf.endchar]
		fragment_lower = fragment.lower()
		tokens = defaultdict(int)
		for t in wf.matches:
			txt = t.text.lower()
			_len = len(txt)
			idx = tokens.get(txt)
			idx = fragment_lower.find(txt, idx)
			if idx >=0:
				endidx = idx + _len
				mrange = _Range(idx, endidx, txt)
				if _is_word_start(idx, fragment) and _is_word_end(endidx, fragment):
					matches.append(mrange)
				tokens[t.text] = endidx 
				
		matches = cls._clean_ranges(matches) #TODO: Do we have to check this?
		result = _SearchFragment()
		result.text = fragment
		result.matches = matches if matches else ()
		return result
	
	@classmethod
	def create_from_terms(cls, text, termset):
		matches = []
		fragment = text
		fragment_lower = fragment.lower()
		termset = [term.lower() for term in termset]
		
		for term in termset:
			idx = 0
			_len = len(term)
			idx = fragment_lower.find(term, idx)
			while idx >=0:
				endidx = idx + _len
				mrange = _Range(idx, endidx, term)
				matches.append(mrange)
				idx = endidx
				idx = fragment_lower.find(term, idx)
			
		matches = cls._clean_ranges(matches)
		result = _SearchFragment()
		result.text = fragment
		result.matches = matches if matches else ()
		return result

def _prune_fragments(termset, snippet, fragments):
	result = []
	snippets = []
	_len = len(termset)
	if _len == 1:
		return snippet, fragments
	
	for sf in fragments:
		matches = sf.matches
		matched_len = len(matches)
		if matched_len < _len:
			continue
		
		idx = 0
		tmp = []
		while idx < len(matches):
			subs = matches[idx:idx+_len]
			if len(subs) != _len:
				break
			zipped = zip(subs, termset)
			matched = reduce(lambda x, t: x and t[0].match(t[1]), zipped, True)
			if matched:
				idx = idx + _len
				tmp.extend(subs)
			else:
				idx += 1
				
		if tmp:
			snippets.append(sf.text)
			sf.matches = tmp
			result.append(sf)
		
	snippet = '...'.join(snippets)
	return snippet, result

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
			sf = _SearchFragment.create_from_whoosh_fragment(f)
			search_fragments.append(sf)	
		snippet = formatter(text, fragments)
			
		logger.log(loglevels.TRACE, 'Snippet "%r", Fragments %r)', snippet, fragments)
	else:
		snippet = text
		logger.log(loglevels.TRACE, 'Creating fragments from terms ("%r", "%r")', termset, snippet)
		search_fragments = [_SearchFragment.create_from_terms(text, termset)]
		
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

