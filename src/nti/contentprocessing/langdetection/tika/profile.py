#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import math
import collections

def arraycopy(source, sourcepos, dest, destpos, numelem):
	dest[destpos:destpos+numelem] = source[sourcepos:sourcepos+numelem]

class LanguageProfile(object):

	DEFAULT_NGRAM_LENGTH = 3

	n = 1
	count = 0

	def __init__(self, content=None, length=DEFAULT_NGRAM_LENGTH):
		self.length = length
		self.buffer = ['', '', '_']
		self.ngrams = collections.defaultdict(int)

	def write(self, cbuf):
		text = cbuf.lower()
		for c in text:
			if c.isalpha():
				self.addLetter(c)
			else:
				self.addSeparator()

	def addLetter(self, c):
		arraycopy(self.buffer, 1, self.buffer, 0, len(buffer) - 1)
		self.buffer[-1] = c
		self.n +=1
		if self.n >= len(self.buffer):
			self.add(''.join(self.buffer))
	
	def addSeparator(self):
		self.addLetter('_')
		self.n = 1

	def close(self):
		self.addSeparator()

	def add(self, ngram, count=1):
		if self.length != len(ngram):
			raise ValueError('Unable to add an ngram of incorrect length')

		self.ngrams[ngram] +=count
		self.count += count;

	def getCount(self, ngram):
		return self.ngrams.get(ngram)

	def distance(self, that):
		
		if self.length != that.length:
			raise ValueError("Unable to calculate distance of language profiles")

		sumOfSquares = 0.0;
		thisCount = max(self.count, 1.0)
		thatCount = max(self.count, 1.0)

		ngrams = set();
		ngrams.update(self.ngrams.keys())
		ngrams.update(that.ngrams.keys())
		for ngram in ngrams:
			thisFrequency = self.getCount(ngram) / float(thisCount)
			thatFrequency = that.getCount(ngram) / float(thatCount)
			difference = thisFrequency - thatFrequency
			sumOfSquares += difference * difference
		
		return math.sqrt(sumOfSquares)

	def __str__(self):
		return str(dict(self.ngrams))
