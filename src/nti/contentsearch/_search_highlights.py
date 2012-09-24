from __future__ import print_function, unicode_literals

import re
from collections import defaultdict

from zope import schema
from zope import component
from zope import interface

from whoosh import analysis
from whoosh import highlight

from nti.externalization import interfaces as ext_interfaces

from nti.contentsearch import interfaces as search_interfaces

import logging
logger = logging.getLogger( __name__ )

WORD_HIGHLIGHT  = "WordHighlight"
WHOOSH_HIGHLIGHT = "WhooshHighlight"

_default_analyzer = None
_default_expression = "\w+(\.?\w+)*"
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
	return frozenset(terms)

def _get_default_analyzer():
	global _default_analyzer
	if _default_analyzer is None:
		sw_util = component.queryUtility(search_interfaces.IStopWords) 
		stoplist = sw_util.stopwords() if sw_util else analysis.STOP_WORDS
		tokenizer = analysis.RegexTokenizer(expression=_default_expression, gaps=False)
		lc_filter = analysis.LowercaseFilter()
		stopword_filter = analysis.StopFilter(stoplist=stoplist)
		_default_analyzer = analysis.CompositeAnalyzer(tokenizer, lc_filter, stopword_filter)
	return _default_analyzer

def _set_matched_filter(tokens, termset):
	for t in tokens:
		t.matched = t.text in termset
		yield t
	
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
		result = {'text': self.text or u'',
				  'matches': self.matches}
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
				matches.append((idx, endidx))
				tokens[t.text] = endidx 
			
		result = _SearchFragment()
		result.text = fragment
		result.matches = matches if matches else ()
		return result
		
def word_fragments_highlight(query, text, maxchars=300, surround=50, top=3, analyzer=None, order=highlight.FIRST):
	text = unicode(text)	
	termset = _get_terms(query)
	scorer = highlight.BasicFragmentScorer()
	analyzer = analyzer or _get_default_analyzer()
	formatter = highlight.NullFormatter() #  highlight.UppercaseFormatter()
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
	
	tokens = analyzer(text, chars=True, mode="query", removestops=False)
	tokens = _set_matched_filter(tokens, termset)
	fragments = fragmenter.fragment_tokens(text, tokens)
	fragments = highlight.top_fragments(fragments, top, scorer, order)
	
	search_fragments = []
	for f in fragments:
		sf = _SearchFragment.create_from_whoosh_fragment(f)
		search_fragments.append(sf)	
		
	snippet = formatter(text, fragments)
	return snippet, search_fragments

def word_content_highlight(query, text, maxchars=300, surround=50, top=3, analyzer=None):
	terms = _get_terms(query)
	analyzer = analyzer or _get_default_analyzer()
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
	formatter = highlight.NullFormatter() # highlight.UppercaseFormatter()
	result = highlight.highlight(text, terms, analyzer, fragmenter, formatter, top=top)
	return result

