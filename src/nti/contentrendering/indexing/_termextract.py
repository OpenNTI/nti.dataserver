# -*- coding: utf-8 -*-
"""
TermExtract key word extractor.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from nti.contentprocessing.keyword import term_extract_key_words
from nti.contentprocessing.keyword import interfaces as cp_interfaces

@interface.implementer( cp_interfaces.ITermExtractFilter)
class _DefaultKeyWordFilter(object):

	def __init__(self, single_strength_min_occur=3, max_limit_strength=2):
		self.max_limit_strength = max_limit_strength
		self.single_strength_min_occur = single_strength_min_occur

	def __call__(self, word, occur, strength):
		result = (strength == 1 and occur >= self.single_strength_min_occur) or (strength <= self.max_limit_strength)
		result = result and len(word) > 1
		return result

def extract_key_words(tokenized_words, max_words=10):
	"""
	extract key words for the specified list of tokens
	
	:param tokenized_words: List of tokens (words)
	:param max_words: Max number of words to return
	"""
	records = term_extract_key_words(tokenized_words, "indexer")
	keywords = []
	for r in records[:max_words]:
		word = r.token
		terms = getattr(r, 'terms', ())
		if terms: word = r.terms[0] # pick the first word
		keywords.append(unicode(word.lower()))
	return keywords.sort()
