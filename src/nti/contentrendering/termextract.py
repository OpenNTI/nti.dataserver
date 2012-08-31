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

class DefaultFilter(object):

	def __init__(self, single_strength_min_occur=3, no_limit_strength=2):
		self.no_limit_strength = no_limit_strength
		self.single_strength_min_occur = single_strength_min_occur

	def __call__(self, word, occur, strength):
		return (strength == 1 and occur >= self.single_strength_min_occur) or (strength >= self.no_limit_strength)

class TermExtractor(object):

	NOUN = 1
	SEARCH = 0

	def __init__(self, term_filter=None):
		self.term_filter = term_filter or DefaultFilter()

	def _tracker(self, term, norm, multiterm, terms):
		multiterm.append((term, norm))
		terms.setdefault(norm, 0)
		terms[norm] += 1
	
	def extract(self, tagged_terms):
		terms = {}
		# phase 1: A little state machine is used to build simple and
		# composite terms.
		multiterm = []
		state = self._SEARCH
		for term, tag, norm in tagged_terms:
			if state == self._SEARCH and tag.startswith('N'):
				state = self._NOUN
				self._tracker(term, norm, multiterm, terms)
			elif state == self._SEARCH and tag == 'JJ' and term[0].isupper():
				state = self._NOUN
				self._tracker(term, norm, multiterm, terms)
			elif state == self._NOUN and tag.startswith('N'):
				self._tracker(term, norm, multiterm, terms)
			elif state == self._NOUN and not tag.startswith('N'):
				state = self._SEARCH
				if len(multiterm) > 1:
					word = ' '.join([word for word, norm in multiterm])
					terms.setdefault(word, 0)
					terms[word] += 1
				multiterm = []
		# phase 2: Only select the terms that fulfill the filter criteria.
		# also create the term strength.
		return [
			(word, occur, len(word.split()))
			for word, occur in terms.items()
			if self.filter(word, occur, len(word.split()))]

