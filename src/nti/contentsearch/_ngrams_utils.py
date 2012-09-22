from __future__ import print_function, unicode_literals

from zope import schema
from zope import component
from zope import interface

from whoosh import analysis

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
	u = component.getUtility(INgramComputer)
	result = u.compute(text)
	return unicode(result)

class INgramComputer(interface.Interface):
	minsize = schema.Int(title="min ngram size", required=True)
	minsize = schema.Int(title="max ngram size", required=True)
	unique = schema.Bool(title="flag to return unique ngrams", required=True)
	at_start = schema.Bool(title="flag to return ngrams from the start of the word ", required=True)
	
	def compute(text):
		"""compute the ngrams for the specified text"""

@interface.implementer( INgramComputer )		
class _DefaultNgramComputer(object):
	
	minsize = 3
	maxsize = 6
	unique = True
	at_start = True
	
	def compute(self, text):
		if text:
			at = 'start' if self.at_start else 'end'
			tokens = ngram_tokens(text, self.minsize, self.maxsize, at, self.unique)
			result = [token.text for token in tokens]
			result = ' '.join(sorted(result, cmp=lambda x,y: cmp(x, y)))
		else:
			result = u''
		return result
	