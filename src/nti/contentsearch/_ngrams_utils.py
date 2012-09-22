from __future__ import print_function, unicode_literals

from zope import component
from zope import interface

from whoosh import analysis

from nti.contentsearch.common import default_ngram_minsize
from nti.contentsearch.common import default_ngram_maxsize
from nti.contentsearch import interfaces as search_interfaces

import logging
logger = logging.getLogger( __name__ )

def ngram_tokens(text, minsize=3, maxsize=10, at='start', unique=True, lower=True):
	tokenizer = analysis.RegexTokenizer()
	ng_filter = analysis.NgramFilter(minsize=minsize, maxsize=maxsize, at=at)
	text = text.lower() if lower else text
	stream = tokenizer(unicode(text.lower()))
	if not unique:
		result = [token.copy() for token in ng_filter(stream)]
	else:
		result = {token.text:token.copy() for token in ng_filter(stream)}.values()
	return result
		
def ngrams(text):
	u = component.getUtility(search_interfaces.INgramComputer)
	result = u.compute(text)
	return unicode(result)

@interface.implementer( search_interfaces.INgramComputer )		
class _DefaultNgramComputer(object):
	
	minsize = default_ngram_minsize
	maxsize = default_ngram_maxsize
	
	def compute(self, text):
		if text:
			tokens = ngram_tokens(text, self.minsize, self.maxsize)
			result = [token.text for token in tokens]
			result = ' '.join(sorted(result, cmp=lambda x,y: cmp(x, y)))
		else:
			result = u''
		return result
	