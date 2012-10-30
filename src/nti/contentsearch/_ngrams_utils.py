from __future__ import print_function, unicode_literals

from zope import component
from zope import interface

from whoosh import analysis

import repoze.lru

from nti.contentsearch.common import default_ngram_minsize
from nti.contentsearch.common import default_ngram_maxsize
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.common import default_word_tokenizer_expression

import logging
logger = logging.getLogger( __name__ )

def _text_or_token(token, text_only=False):
	return token.text if text_only else token.copy()

def ngram_filter(text, minsize=3, maxsize=10, at='start', unique=True, lower=True, text_only=True):
	text = text.lower() if lower else text
	ng_filter = analysis.NgramFilter(minsize=minsize, maxsize=maxsize, at=at)
	tokenizer = analysis.RegexTokenizer(expression=default_word_tokenizer_expression)
	stream = tokenizer(unicode(text))
	if not unique:
		result = [_text_or_token(token, text_only) for token in ng_filter(stream)]
	else:
		result = {_text_or_token(token, text_only) for token in ng_filter(stream)}
	return result
		
@repoze.lru.lru_cache(1000)
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
			result = ngram_filter(text, self.minsize, self.maxsize, unique=True, text_only=True)
			result = ' '.join(result)
		else:
			result = u''
		return result
	