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

#!/usr/bin/env python

import os
import re
from collections import defaultdict

from nltk.tokenize import RegexpTokenizer

from nti.contentprocessing.stemmers import PorterStemmer
from nti.contentprocessing.taggers import get_backoff_ngram_tagger

class DefaultFilter(object):

	def __init__(self, single_strength_min_occur=3, no_limit_strength=2):
		self.no_limit_strength = no_limit_strength
		self.single_strength_min_occur = single_strength_min_occur

	def __call__(self, word, occur, strength):
		return (strength == 1 and occur >= self.single_strength_min_occur) or (strength >= self.no_limit_strength)

class NormRecord(object):
	
	def __init__(self, norm, occur, strength, terms=()):
		self.norm = norm
		self.occur = occur
		self.strength = strength
		self.terms = sorted(terms) if terms else () 

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

default_tokenizer = RegexpTokenizer(r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*",
									flags = re.MULTILINE | re.DOTALL)
	
def extract_key_words_from_tokens(tokenized_words, extractor=None, tagger=None, stemmer=None):
	tagger = tagger or get_backoff_ngram_tagger()
	stemmer = stemmer or PorterStemmer()
	extractor = extractor or TermExtractor()
	tagged_items = tagger.tag(tokenized_words)
	tagged_terms = []
	for token, tag in tagged_items:
		root = stemmer.stem(token) if stemmer else token
		tagged_terms.append((token, tag, root))
	result = extractor.extract(tagged_terms)
	return result

def extract_key_words_from_text(content, extractor=None, tokenizer=default_tokenizer, tagger=None, stemmer=None):
	tokenized_words = tokenizer.tokenize(content)
	return extract_key_words_from_tokens(tokenized_words, extractor=extractor, tagger=extractor, stemmer=stemmer)

extract_key_words = extract_key_words_from_text

if __name__ == '__main__':
	import sys
	args = sys.argv[1:]
	if args:
		with open(os.path.expanduser(args[0]),"r") as f:
			content = f.read()
		print extract_key_words(content)
