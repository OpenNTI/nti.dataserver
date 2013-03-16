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

class TrainerData(object):

	def __init__(self):
		self.trigrams = {}  # tri-grams storage
		self.characters = 0  # number of characters
		self.total_trigrams = 0  # number of tri-grams

	def __iadd__(self, other):
		if isinstance(other, TrainerData):
			self.characters += other.characters
			self.total_trigrams += other.total_trigrams
			for k, v in other.trigrams.items():
				self.trigrams.setdefault(k, 0)
				self.trigrams[k] += v
		return self

def create_trigrams(text, data):
	"""Creates trigrams from characters."""
	text = re.sub(r'[\n\r\s]+', r" ", text.lower())
	data.characters = data.characters + len(text)
	for i in range(len(text) - 2):
		data.total_trigrams += 1
		trigram = text[i:i + 3]
		data.trigrams.setdefault(trigram, 0)
		data.trigrams[trigram] += 1

def calc_prob(data):
	"""Calculate the probabilities for each trigram."""
	for x in data.trigrams.keys():
		data.trigrams[x] = float(data.trigrams[x]) / float(data.total_trigrams)
	return data

def eliminate_frequences(minfreq, data):
	"""Eliminates all trigrams with a frequency <= minfreq"""
	for x in data.trigrams.keys():
		if data.trigrams[x] <= minfreq:
			value = data.trigrams.pop(x, 0)
			data.total_trigrams -= value
	return data

def clean_text_sc(text, lang='en'):
	"""Eliminates punctuation symbols from the submitted text."""
	pattern = component.getUtility(cp_intefraces.IPunctuationCharPattern, name=lang)
	result = re.sub(pattern, ' ', text)
	return result

def create_trigram_nsc(text, data):
	text = clean_text_sc(text)
	return create_trigrams(text, data)

def clean_pbig(data, lang='en'):
	"""Eliminate tri-grams that contain punctuation marks."""
	pattern = component.getUtility(cp_intefraces.IPunctuationCharPattern, name=lang)
	for t in data.trigrams.keys():
		if pattern.search(t):
			value = data.trigrams.pop(t, 0)
			data.total_trigrams -= value
	return data

class TrigramTrainer(object):

	def __init__(self):
		self.data = TrainerData()

	@property
	def trigrams(self):
		return self.data.trigrams

	@property
	def total_trigrams(self):
		return self.data.total_trigrams

	@property
	def characters(self):
		return self.data.characters

	def create_trigrams(self, text):
		return create_trigrams(text, self.data)

	def calc_prob(self):
		return calc_prob(self.data)

	def eliminate_frequences(self, minfreq):
		return eliminate_frequences(minfreq, self.data)

	def create_trigram_nsc(self, text):
		return create_trigram_nsc(text, self.data)

	def clean_text_sc(self, text, lang='en'):
		return clean_text_sc(text, lang)

	def clean_pbig(self, lang='en'):
		return clean_pbig(self.data, lang)

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
