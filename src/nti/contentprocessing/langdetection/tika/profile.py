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

DEFAULT_NGRAM_LENGTH = 3
	
def arraycopy(source, sourcepos, dest, destpos, numelem):
	dest[destpos:destpos+numelem] = source[sourcepos:sourcepos+numelem]

class LanguageProfile(object):

	__slots__ = ('n', 'count', 'length', 'buffer', 'ngrams')

	def __init__(self, content=None, length=DEFAULT_NGRAM_LENGTH):
		self.n = 1
		self.count = 0
		self.length = length
		self.buffer = ['', '', '_']
		self.ngrams = collections.defaultdict(int)
		if content:
			self.write(content)

	def write(self, cbuf):
		for c in cbuf:
			c = c.lower()
			if c.isalpha():
				self.addLetter(c)
			else:
				self.addSeparator()

	def addLetter(self, c):
		arraycopy(self.buffer, 1, self.buffer, 0, len(self.buffer) - 1)
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
		return self.ngrams.get(ngram, 0.0)

	def distance(self, that):
		
		if self.length != that.length:
			raise ValueError("Unable to calculate distance of language profiles")

		sumOfSquares = 0.0;
		thisCount = max(self.count, 1.0)
		thatCount = max(that.count, 1.0)

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
