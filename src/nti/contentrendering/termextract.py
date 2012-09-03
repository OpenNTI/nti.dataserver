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

	_NOUN = 1
	_SEARCH = 0

	def __init__(self, term_filter=None):
		self.term_filter = term_filter or DefaultFilter()

	def _tracker(self, term, norm, multiterm, terms):
		multiterm.append((term, norm))
		terms.setdefault(norm, 0)
		terms[norm] += 1
	
	def extract(self, tagged_terms=()):
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
			if self.term_filter(word, occur, len(word.split()))]
	
# for the time being we assume the training sents comes
# from the brown corpus
_train_sents = None
def default_train_sents():
	global _train_sents
	if _train_sents is None:
		try:
			from nltk.corpus import brown
			_train_sents = brown.tagged_sents()
		except:
			_train_sents = ()
	return _train_sents

from nltk.tag import UnigramTagger, BigramTagger, TrigramTagger, DefaultTagger

# build  a built up tagger 
def backoff_tagger(train_sents, start_tagger=None, tagger_classes=()): 
	backoff = start_tagger
	for cls in tagger_classes: 
		backoff = cls(train_sents, backoff=backoff) 
	return backoff

# return default tagger using the default training sentences
def default_tagger():
	train_sents = default_train_sents()
	tagger = DefaultTagger('NN')
	if train_sents:
		tagger = backoff_tagger(train_sents=train_sents, start_tagger=tagger,
								tagger_classes=(UnigramTagger, BigramTagger, TrigramTagger))
	return tagger


import re
from nltk import PorterStemmer
from nltk.tokenize import RegexpTokenizer

default_tokenizer = RegexpTokenizer(r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*",
									flags = re.MULTILINE | re.DOTALL)
	
def extract_key_words(content, extractor=None, tokenizer=default_tokenizer, tagger=None, stemmer=None):
	tagger = tagger or default_tagger()
	stemmer = stemmer or PorterStemmer()
	extractor = extractor or TermExtractor()
	tokenized_words = tokenizer.tokenize(content)
	tagged_items = tagger.tag(tokenized_words)
	tagged_terms = []
	for token, tag in tagged_items:
		root = stemmer.stem(token) if stemmer else token
		tagged_terms.append((token, tag, root))
	result = extractor.extract(tagged_terms)
	return result

if __name__ == '__main__':
	import os
	import sys
	
	args = sys.argv[1:]
	if args:
		with open(os.path.expanduser(args[0]),"r") as f:
			content = f.read()
		print extract_key_words(content)
