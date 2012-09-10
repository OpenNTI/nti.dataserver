from __future__ import print_function, unicode_literals

from whoosh import analysis
from whoosh import highlight

from nti.contentsearch._ngrams_utils import ngram_tokens

import logging
logger = logging.getLogger( __name__ )

WORD_HIGHLIGHT  = "WordHighlight"
NGRAM_HIGHLIGHT = "NGRAMHighlight"
WHOOSH_HIGHLIGHT = "WhooshHighlight"

def _set_matched_filter(tokens, termset, text, multiple_match=True):
	index = {} if multiple_match else None
	for t in tokens:
		t.matched = t.text in termset
		if t.matched:
			
			idx = 0
			if multiple_match:
				a = index.get(t.text, None)
				if not a:
					a = [0]
					index[t.text] = a
				idx = a[-1]
				
			t.startchar = text.find(t.text, idx)
			t.endchar = t.startchar + len(t.text)
			
			if multiple_match:
				a.append(t.startchar+1)
		else:
			t.startchar = 0
			t.endchar = len(text)
		yield t
		
def ngram_content_highlight(query, text, maxchars=300, surround=50, order=highlight.FIRST, top=3, 
							multiple_match=False, minsize=3, *args, **kwargs):
	"""
	highlight based on ngrams
	"""
	text = unicode(text)
	text_lower = unicode(text.lower())
	
	query = unicode(query.lower())
	termset = frozenset([query])
		
	scorer = highlight.BasicFragmentScorer()
	tokens = ngram_tokens(text_lower, unique=not multiple_match, minsize=minsize)
	tokens = _set_matched_filter(tokens, termset, text_lower, multiple_match)
	
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
	fragments = fragmenter.fragment_tokens(text, tokens)
	fragments = highlight.top_fragments(fragments, top, scorer, order)
	
	formatter = highlight.NullFormatter() #  highlight.UppercaseFormatter()
	return formatter(text, fragments)

def word_content_highlight(query, text, analyzer=None, maxchars=300, surround=50, *args, **kwargs):
	"""
	whoosh highlight based on words
	"""
	terms = frozenset([query])
	analyzer = analyzer or analysis.SimpleAnalyzer()
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
	formatter = highlight.NullFormatter() # highlight.UppercaseFormatter()
	return highlight.highlight(text, terms, analyzer, fragmenter, formatter)


