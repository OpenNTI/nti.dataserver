#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TermExtract key word extractor.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.contentprocessing.keyword import term_extract_key_words
from nti.contentprocessing.keyword.interfaces import ITermExtractFilter

@interface.implementer(ITermExtractFilter)
class _DefaultKeyWordFilter(object):

	def __init__(self, single_strength_min_occur=3, max_limit_strength=2):
		self.max_limit_strength = max_limit_strength
		self.single_strength_min_occur = single_strength_min_occur

	def __call__(self, word, occur, strength):
		result = (strength == 1 and occur >= self.single_strength_min_occur) or \
				 (strength <= self.max_limit_strength)
		result = result and len(word) > 1
		return result

def extract_key_words(tokenized_words, max_words=10, lang='en', filtername='indexer'):
	"""
	extract key words for the specified list of tokens
	
	:param tokenized_words: List of tokens (words)
	:param max_words: Max number of words to return
	"""
	keywords = []
	records = term_extract_key_words(tokenized_words, lang=lang, filtername=filtername)
	for r in records[:max_words]:
		word = r.token
		terms = getattr(r, 'terms', ())
		if terms: word = r.terms[0] # pick the first word
		keywords.append(unicode(word.lower()))
	return keywords.sort()
