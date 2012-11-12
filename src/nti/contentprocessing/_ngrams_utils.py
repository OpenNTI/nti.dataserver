from __future__ import print_function, unicode_literals

from zope import component
from zope import interface

from whoosh import analysis

import repoze.lru

from nti.contentprocessing import default_ngram_minsize
from nti.contentprocessing import default_ngram_maxsize
from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentprocessing._content_utils import split_content
from nti.contentprocessing import default_word_tokenizer_expression

import logging
logger = logging.getLogger( __name__ )

def _text_or_token(token, text_only=False):
	return token.text if text_only else token.copy()

def whoosh_ngram_filter(text, minsize=3, maxsize=None, at='start', unique=True, lower=True, text_only=True):
	maxsize = maxsize or len(text)
	text = text.lower() if lower else text
	ng_filter = analysis.NgramFilter(minsize=minsize, maxsize=maxsize, at=at)
	tokenizer = analysis.RegexTokenizer(expression=default_word_tokenizer_expression)
	stream = tokenizer(unicode(text))
	if not unique:
		result = [_text_or_token(token, text_only) for token in ng_filter(stream)]
	else:
		result = {_text_or_token(token, text_only) for token in ng_filter(stream)}
	return result
	
@repoze.lru.lru_cache(5000)
def _ngram_cache(text, minsize=3, maxsize=None, unique=True, lower=True):
	result = []
	maxsize = maxsize or len(text)
	text = text.lower() if lower else text
	limit = min(maxsize, len(text))
	for size in xrange(minsize, limit + 1):
		ngram = text[:size]
		result.append(ngram)
	return tuple(result)
	
def ngram_filter(text, minsize=3, maxsize=None, unique=True, lower=True):
	tokens = split_content(text)
	result = set() if unique else []
	for text in tokens:
		ngrams = _ngram_cache(text, minsize, maxsize, unique, lower)
		if unique:
			result.update(ngrams)
		else:
			result.extend(ngrams)
	return result

@repoze.lru.lru_cache(100)
def compute_ngrams(text):
	u = component.getUtility(cp_interfaces.INgramComputer)
	result = u.compute(text)
	return unicode(result)

@interface.implementer( cp_interfaces.INgramComputer )		
class _DefaultNgramComputer(object):
	
	minsize = default_ngram_minsize
	maxsize = default_ngram_maxsize
	
	def compute(self, text):
		if text:
			result = ngram_filter(text, self.minsize, self.maxsize)
			result = ' '.join(result)
		else:
			result = u''
		return result
	