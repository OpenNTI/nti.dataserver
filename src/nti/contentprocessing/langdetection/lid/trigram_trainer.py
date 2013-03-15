# -*- coding: utf-8 -*-
"""
Lidtrainer processes

author = "Damir Cavar <damir@cavar.me>"
http://www.cavar.me/damir/LID/resources/lidtrainer.py.html

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import re
import gzip

from zope import component

from ...import _content_utils as cu
from ...import interfaces as cp_intefraces

class TrigramTrainer(object):

	def __init__(self):
		self.trigrams = {}  # tri-grams storage
		self.characters = 0  # number of characters
		self.total_trigrams = 0  # number of tri-grams

	@classmethod
	def g_create_trigrams(cls, text, trigrams, characters, total_trigrams):
		text = re.sub(r'[\n\r\s]+', r" ", text.lower())
		characters = characters + len(text)

		for i in range(len(text) - 2):
			total_trigrams += 1
			trigram = text[i:i + 3]
			trigrams.setdefault(trigram, 0)
			trigrams[trigram] += 1

		return characters, total_trigrams

	def create_trigrams(self, text):
		"""Creates trigrams from characters."""
		self.characters, self.total_trigrams = \
				self.g_create_trigrams(text, self.trigrams, self.characters, self.total_trigrams)
		return self.characters, self.total_trigrams

	@classmethod
	def g_calc_prob(cls, trigrams, total_trigrams):
		for x in trigrams.keys():
			trigrams[x] = float(trigrams[x]) / float(total_trigrams)

	def calc_prob(self):
		"""Calculate the probabilities for each trigram."""
		self.g_calc_prob(self.trigrams, self.total_trigrams)

	@classmethod
	def g_eliminate_frequences(cls, trigrams, minfreq, total_trigrams):
		for x in trigrams.keys():
			if trigrams[x] <= minfreq:
				value = trigrams.pop(x, 0)
				total_trigrams -= value
		return total_trigrams

	def eliminate_frequences(self, minfreq):
		"""Eliminates all trigrams with a frequency <= minfreq"""
		self.total_trigrams = self.g_eliminate_frequences(self.trigrams, minfreq, self.total_trigrams)

	@classmethod
	def g_create_trigram_nsc(cls, text, trigrams, characters, total_trigrams):
		text = cls.g_clean_text_sc(text)
		return cls.g_create_trigrams(text, trigrams, characters, total_trigrams)

	def create_trigram_nsc(self, text):
		"""Creates trigrams without punctuation symbols."""
		self.characters, self.total_trigrams = \
				self.g_create_trigram_nsc(text, self.trigrams, self.characters, self.total_trigrams)
		return self.characters, self.total_trigrams

	@classmethod
	def g_clean_text_sc(cls, text, lang='en'):
		"""Eliminates punctuation symbols from the submitted text."""
		pattern = component.getUtility(cp_intefraces.IPunctuationCharPattern, name=lang)
		result = re.sub(pattern, ' ', text)
		return result

	clean_text_sc = g_clean_text_sc

	@classmethod
	def g_clean_pbig(cls, trigrams, total_trigrams, lang='en'):
		pattern = component.getUtility(cp_intefraces.IPunctuationCharPattern, name=lang)
		for t in trigrams.keys():
			if pattern.search(t):
				value = trigrams.pop(t, 0)
				total_trigrams -= value
		return total_trigrams

	def clean_pbig(self):
		"""Eliminate tri-grams that contain punctuation marks."""
		self.total_trigrams = self.g_clean_pbig(self.trigrams, self.total_trigrams)
		return self.total_trigrams

	@classmethod
	def process_files(cls, dpath, minfreq=2, trainer=None, calc_prob=True, tokenize=False, lang="en"):
		"""Train content found in files in a particular directory"""
		trainer = TrigramTrainer() if trainer is None else trainer
		for fn in os.listdir(dpath):
			fn = os.path.join(dpath, fn)
			if os.path.isdir(fn): continue
			try:
				if fn.endswith(".gz"):
					fo = gzip.open(fn)
				else:
					fo = open(fn, "r")
				try:
					text = fo.read()
					if tokenize:
						text = cu.get_content(text, lang)
					else:
						text = trainer.clean_text_sc(text, lang)
					trainer.create_trigrams(text)
				finally:
					fo.close()
			except IOError:
				pass

		pairs = ()
		trainer.eliminate_frequences(minfreq)
		if calc_prob:
			trainer.calc_prob()
			pairs = zip(trainer.trigrams.values(), trainer.trigrams.keys())
			pairs.sort(reverse=True)
		return trainer, pairs
