# -*- coding: utf-8 -*-
"""
NGRAM processing utilities

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import repoze.lru

from zope import component
from zope import interface

from . import default_ngram_minsize
from . import default_ngram_maxsize
from . import interfaces as cp_interfaces
from ._content_utils import split_content

@repoze.lru.lru_cache(5000)
def _ngram_cache(text, minsize=3, maxsize=None, unique=True, lower=True):
	result = []
	maxsize = maxsize or len(text)
	text = text.lower() if lower else text
	limit = min(maxsize, len(text))
	for size in xrange(minsize, limit + 1):
		ngram = text[:size]
		result.append(ngram)
	return result

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
def compute_ngrams(text, language="en"):
	u = component.getUtility(cp_interfaces.INgramComputer, name=language)
	result = u.compute(text) if text else u''
	return unicode(result)

@interface.implementer(cp_interfaces.INgramComputer)
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
