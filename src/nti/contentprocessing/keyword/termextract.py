#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TermExtract keyword extractor

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from collections import defaultdict

from zope import interface
from zope import component

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash

from .. import taggers
from .. import stemmers
from .. import tokenize_content

from .interfaces import ITermExtractFilter
from .interfaces import ITermExtractKeyWord
from .interfaces import ITermExtractKeyWordExtractor

@interface.implementer(ITermExtractFilter)
class DefaultFilter(object):

	def __init__(self, single_strength_min_occur=3, no_limit_strength=2):
		self.no_limit_strength = no_limit_strength
		self.single_strength_min_occur = single_strength_min_occur

	def __call__(self, word, occur, strength):
		return	(strength == 1 and occur >= self.single_strength_min_occur) or \
				(strength >= self.no_limit_strength)

	def __repr__(self):
		return "DefaultFilter(%s, %s)" % (self.no_limit_strength,
										  self.single_strength_min_occur)

	__str__ = __repr__

def term_extract_filter(name=u''):
	result = component.queryUtility(ITermExtractFilter, name=name)
	return result or DefaultFilter()

@WithRepr
@EqHash('norm','terms','strength','frequency')
@interface.implementer(ITermExtractKeyWord)
class NormRecord(object):

	def __init__(self, norm, frequency, strength, terms=()):
		self.norm = norm
		self.strength = strength
		self.frequency = frequency
		self.terms = sorted(terms) if terms else ()

	@property
	def token(self):
		return self.norm

	@property
	def relevance(self):
		return self.frequency

	@property
	def occur(self):
		return self.frequency

class TermExtractor(object):

	_NOUN = 1
	_SEARCH = 0

	def __init__(self, term_filter=None):
		self.term_filter = term_filter or term_extract_filter()

	def _tracker(self, term, norm, multiterm, terms, terms_norm):
		multiterm.append((term, norm))
		terms.setdefault(norm, 0)
		terms[norm] += 1
		terms_norm[norm].add(term.lower())

	def extract(self, tagged_terms=()):
		terms = {}
		# phase 1: A little state machine is used to build simple and
		# composite terms.
		multiterm = []
		terms_norm = defaultdict(set)

		state = self._SEARCH
		for term, tag, norm in tagged_terms:
			if state == self._SEARCH and tag.startswith('N'):
				state = self._NOUN
				self._tracker(term, norm, multiterm, terms, terms_norm)
			elif state == self._SEARCH and tag == 'JJ' and term[0].isupper():
				state = self._NOUN
				self._tracker(term, norm, multiterm, terms, terms_norm)
			elif state == self._NOUN and tag.startswith('N'):
				self._tracker(term, norm, multiterm, terms, terms_norm)
			elif state == self._NOUN and not tag.startswith('N'):
				state = self._SEARCH
				if len(multiterm) > 1:
					word = ' '.join([word for word, norm in multiterm])
					terms.setdefault(word, 0)
					terms[word] += 1
				multiterm = []
		# phase 2: Only select the terms that fulfill the filter criteria.
		# also create the term strength.
		result = [	NormRecord(norm, occur, len(norm.split()), terms_norm.get(norm, ()))
			 		for norm, occur in terms.items()
			 		if self.term_filter(norm, occur, len(norm.split())) ]
		result = sorted(result, reverse=True, key=lambda x: x.occur)

		return result

@interface.implementer(ITermExtractKeyWordExtractor)
class _DefaultKeyWorExtractor():

	def __call__(self, content, lang='en', filtername=u'', *args, **kwargs):

		if isinstance(content, six.string_types):
			tokenized_words = tokenize_content(content, lang)
		else:
			tokenized_words = content

		tagged_terms = []
		term_filter = term_extract_filter(filtername)
		extractor = TermExtractor(term_filter)
		tagged_items = taggers.tag_tokens(tokenized_words, lang)
		for token, tag in tagged_items:
			root = stemmers.stem_word(token, lang)
			tagged_terms.append((token, tag, root))
		result = extractor.extract(tagged_terms)
		return result
