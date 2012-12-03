##############################################################################
#
# Copyright (c) 2009 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

from __future__ import print_function, unicode_literals

from collections import defaultdict

from zope import interface
from zope import component

from nti.contentprocessing import split_content
from nti.contentprocessing.stemmers import stem_word
from nti.contentprocessing.taggers import tag_tokens
from nti.contentprocessing import interfaces as cp_interfaces

@interface.implementer( cp_interfaces.ITermExtractFilter)	
class DefaultFilter(object):

	def __init__(self, single_strength_min_occur=3, no_limit_strength=2):
		self.no_limit_strength = no_limit_strength
		self.single_strength_min_occur = single_strength_min_occur

	def __call__(self, word, occur, strength):
		return (strength == 1 and occur >= self.single_strength_min_occur) or (strength >= self.no_limit_strength)

@interface.implementer( cp_interfaces.ITermExtractKeyWord )	
class NormRecord(object):
	
	__slots__ = 'norm', 'occur', 'strength', 'terms', 'token'
	
	def __init__(self, norm, occur, strength, terms=()):
		self.norm = norm
		self.occur = occur
		self.strength = strength
		self.terms = sorted(terms) if terms else () 

	@property
	def token(self):
		return self.norm
	
	def __repr__( self ):
		return "NormRecord(%s, %s, %s, %s)" % (self.norm, self.occur, self.strength, self.terms)
	
class TermExtractor(object):

	_NOUN = 1
	_SEARCH = 0

	def __init__(self, term_filter=None):
		self.term_filter = term_filter or DefaultFilter()

	def _tracker(self, term, norm, multiterm, terms, terms_per_norm):
		multiterm.append((term, norm))
		terms.setdefault(norm, 0)
		terms[norm] += 1
		terms_per_norm[norm].add(term.lower())
	
	def extract(self, tagged_terms=()):
		terms = {}
		# phase 1: A little state machine is used to build simple and
		# composite terms.
		multiterm = []
		terms_per_norm = defaultdict(set)
		
		state = self._SEARCH
		for term, tag, norm in tagged_terms:
			if state == self._SEARCH and tag.startswith('N'):
				state = self._NOUN
				self._tracker(term, norm, multiterm, terms, terms_per_norm)
			elif state == self._SEARCH and tag == 'JJ' and term[0].isupper():
				state = self._NOUN
				self._tracker(term, norm, multiterm, terms, terms_per_norm)
			elif state == self._NOUN and tag.startswith('N'):
				self._tracker(term, norm, multiterm, terms, terms_per_norm)
			elif state == self._NOUN and not tag.startswith('N'):
				state = self._SEARCH
				if len(multiterm) > 1:
					word = ' '.join([word for word, norm in multiterm])
					terms.setdefault(word, 0)
					terms[word] += 1
				multiterm = []
		# phase 2: Only select the terms that fulfill the filter criteria.
		# also create the term strength.
		result = [	NormRecord(norm, occur, len(norm.split()), terms_per_norm.get(norm,()))
			 		for norm, occur in terms.items()
			 		if self.term_filter(norm, occur, len(norm.split())) ]
		result = sorted(result, reverse=True, key=lambda x: x.occur)
		
		return result

@interface.implementer( cp_interfaces.IKeyWordExtractor )
class _DefaultKeyWorExtractor():
	
	def __call__(self, content, *args):
		
		if isinstance(content, (list, tuple)):
			tokenized_words = content
		else:
			tokenized_words = split_content(content)
			
		tagged_terms = []
		extractor = TermExtractor(*args)
		tagged_items = tag_tokens(tokenized_words)
		for token, tag in tagged_items:
			root = stem_word(token)
			tagged_terms.append((token, tag, root))
		result = extractor.extract(tagged_terms)
		return result

def extract_key_words(content, *args):
	extractor = component.getUtility(cp_interfaces.IKeyWordExtractor)
	result = extractor(content, *args)
	return result
