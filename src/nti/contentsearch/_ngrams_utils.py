from __future__ import print_function, unicode_literals

from zope import component
from zope import interface

from whoosh import analysis

import repoze.lru

from nti.contentsearch._content_utils import split_content
from nti.contentsearch.common import default_ngram_minsize
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.common import default_word_tokenizer_expression

import logging
logger = logging.getLogger( __name__ )

def _text_or_token(token, text_only=False):
	return token.text if text_only else token.copy()

def whoosh_ngram_filter(text, minsize=3, maxsize=10, at='start', unique=True, lower=True, text_only=True):
	text = text.lower() if lower else text
	ng_filter = analysis.NgramFilter(minsize=minsize, maxsize=maxsize, at=at)
	tokenizer = analysis.RegexTokenizer(expression=default_word_tokenizer_expression)
	stream = tokenizer(unicode(text))
	if not unique:
		result = [_text_or_token(token, text_only) for token in ng_filter(stream)]
	else:
		result = {_text_or_token(token, text_only) for token in ng_filter(stream)}
	return result
	
@repoze.lru.lru_cache(3000)
def _ngram_cache(text, minsize=3, maxsize=10, unique=True, lower=True):
	result = []
	text = text.lower() if lower else text
	limit = min(maxsize, len(text))
	for size in xrange(minsize, limit + 1):
		ngram = text[:size]
		result.append(ngram)
	return tuple(result)
	
def ngram_filter(text, minsize=3, maxsize=None, unique=True, lower=True):
	result = set() if unique else []
	tokens = split_content(text)
	maxsize = maxsize or max(map(len, tokens))
	for text in tokens:
		ngrams = _ngram_cache(text, minsize, maxsize, unique, lower)
		if unique:
			result.update(ngrams)
		else:
			result.extend(ngrams)
	return result

@repoze.lru.lru_cache(1000)
def ngrams(text, minsize=None, maxsize=None):
	u = component.getUtility(search_interfaces.INgramComputer)
	result = u.compute(text)
	return unicode(result)

@interface.implementer( search_interfaces.INgramComputer )		
class _DefaultNgramComputer(object):
	
	maxsize = None
	minsize = default_ngram_minsize
	
	def compute(self, text, minsize=None, maxsize=None):
		if text:
			minsize = minsize or self.minsize
			maxsize = maxsize or self.maxsize
			result = ngram_filter(text, minsize, maxsize)
			result = ' '.join(result)
		else:
			result = u''
		return result
	