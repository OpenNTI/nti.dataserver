#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import time
import codecs
import functools
from array import array

class QuickStringBuffer(object):

	__slots__ = ('value',)

	def __init__(self, value=None):
		if value is None:
			self.value = []
		elif isinstance(value, six.string_types):
			self.value = []
			self.append(value)
		else:
			self.value = value

	def __len__(self):
		return len(self.value)

	def __str__(self):
		return ''.join(self.value)

	def __repr__(self):
		return repr(self.__str__())

	def __getitem__(self, idx):
		return self.value[idx]

	def __eq__(self, other):
		try:
			return self is other or repr(self) == repr(other)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(tuple(self.value))
		return xhash

	def __iter__(self):
		return iter(self.value)

	def lower(self):
		t = [x.lower() for x in self.value]
		return QuickStringBuffer(t)
	
	def clear(self):
		self.value = []
		return self

	def charAt(self, index):
		return self.value[index]

	def append(self, s):
		self.value.extend(s)
		return self

	def subSequence(self, start, end):
		return ''.join(self.value[start:end])

	def write(self, fp):
		for c in self.value:
			fp.write(c)

@functools.total_ordering
class NGramEntry(object):

	__slots__ = ('seq', 'count', 'profile', 'frequency')

	def __init__(self, seq=None, count=0):
		if isinstance(seq, six.string_types):
			self.seq = QuickStringBuffer(seq)
		else:
			self.seq = seq

		self.count = count
		self.profile = None
		self.frequency = 0.0

	def inc(self):
		self.count += 1
		return self

	def write(self, fp):
		self.seq.write(fp)
		return self

	def __len__(self):
		return len(self.seq) if self.seq is not None else 0
	size = __len__

	def __str__(self):
		return repr(self.seq)

	def __repr__(self):
		return "%s(%r, %s, %s)" % (self.__class__.__name__, self.seq,
								   self.count, self.frequency)

	def __eq__(self, other):
		try:
			return self is other or self.seq == other.seq
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return hash(self.seq)

	def __lt__(self, other):
		try:
			return (self.frequency, repr(self.seq)) < (other.frequency, repr(other.seq))
		except AttributeError:
			return NotImplemented

	def __gt__(self, other):
		try:
			return (self.frequency, repr(self.seq)) > (other.frequency, repr(other.seq))
		except AttributeError:
			return NotImplemented

class LanguageProfilerBuilder(object):

	DEFAULT_MIN_NGRAM_LENGTH = 3
	DEFAULT_MAX_NGRAM_LENGTH = 3
	ABSOLUTE_MIN_NGRAM_LENGTH = 3
	ABSOLUTE_MAX_NGRAM_LENGTH = 3

	MAX_SIZE = 1000
	FILE_EXTENSION = "ngp"

	SEPARATOR = u'_'
	SEP_CHARSEQ = QuickStringBuffer(SEPARATOR)

	_sorted = None
	ngramcounts = None
	minLength = DEFAULT_MIN_NGRAM_LENGTH
	maxLength = DEFAULT_MAX_NGRAM_LENGTH

	def __init__(self, name=None, minlen=ABSOLUTE_MIN_NGRAM_LENGTH,
				 maxlen=ABSOLUTE_MAX_NGRAM_LENGTH):
		self.name = name
		self.ngrams = {}
		self.minLength = minlen
		self.maxLength = maxlen
		self.word = QuickStringBuffer()

	def _add_cs(self, cs):
		if (cs == self.SEP_CHARSEQ or cs == self.SEPARATOR):
			return

		nge = self.ngrams.get(cs)
		if nge is None:
			nge = NGramEntry(cs)
			self.ngrams[cs] = nge
		nge.inc()

	def _add_len(self, word, n):
		if isinstance(word, six.string_types):
			word = QuickStringBuffer(word)
		for i in range(0, len(word)-n+1):
			self._add_cs(word.subSequence(i, i + n))
			
	def _add_qsb(self, word):
		wlen = len(word)
		if wlen >= self.minLength:
			_max = min(self.maxLength, wlen)
			for i in range(self.minLength, _max+1):
				self._add_cs(word.subSequence(wlen - i, wlen))
	
	def _add_str(self, word):
		wlen = len(word)
		i = self.minLength
		while i <= self.maxLength and i < wlen:
			self._add_len(word, i)
			i += 1
	
	def add(self, word):
		if isinstance(word, six.string_types):
			self._add_str(word)
		elif isinstance(word, QuickStringBuffer):
			self._add_qsb(word)
		else:
			raise ValueError("Incorrect word %s/%s", type(word), word)
		return self

	def analyze(self, text):
		if self.ngrams:
			self.ngrams.clear()
			self.sorted = None
			self.ngramcounts = None
			
		self.word.clear().append(self.SEPARATOR)
		for c in text:
			c = c.lower()
			if c.isalpha():
				self.add(self.word.append(c))
			else:
				wlen = len(self.word)
				if wlen > 1:
					self.add(self.word.append(self.SEPARATOR))
					self.word.clear().append(self.SEPARATOR)
				
		wlen = len(self.word)
		if wlen > 1:
			self.add(self.word.append(self.SEPARATOR))
		self.normalize()

	def normalize(self):
		if self.ngramcounts is None:
			self.ngramcounts = array(str('i'), (0 for _ in xrange(self.maxLength + 1)))
			for e in self.ngrams.values():
				self.ngramcounts[e.size()] += e.count;

		for e in self.ngrams.values():
			e.frequency = e.count / float(self.ngramcounts[e.size()])

	@property
	def sorted(self):
		if self._sorted is None:
			self._sorted = sorted(self.ngrams.values())
			if len(self._sorted) > self.MAX_SIZE:
				self._sorted = self._sorted[:self.MAX_SIZE]
		return self._sorted

	def getSimilarity(self, another):
		result = 0.0
		for other in another.sorted:
			if other.seq in self.ngrams:
				result += abs((other.frequency - self.ngrams[other.seq].frequency)) / 2.0
			else:
				result += other.frequency;
	
		for other in self.sorted:
			if other.seq in another.ngrams:
				result += abs((other.frequency - another.ngrams[other.seq].frequency)) / 2.0
			else:
				result += other.frequency
				
		return result
	
	def load(self, source, encoding="utf-8"):
		result = 0
		source = open(str(source), "r") if not hasattr(source, "readlines") else source
		try:
			self.ngrams.clear()
			self.ngramcounts = array(str('i'), (0 for _ in xrange(self.maxLength + 1)))
			reader = codecs.getreader(encoding)(source)
			for line in reader.readlines():
				if line and line[0] != '#':
					splits = line.split()
					ngramsequence = splits[0].strip()
					wlen = len(ngramsequence)
					if wlen >= self.minLength and wlen <= self.maxLength:
						ngramcount = int(splits[1].strip())
						en = NGramEntry(ngramsequence, ngramcount)
						self.ngrams[en.seq] = en
						self.ngramcounts[wlen] += ngramcount
						result += 1
		finally:
			source.close()
		self.normalize()
		return result
	
	def save(self, target):
		fp = None
		close = not hasattr(target, "write")
		try:
			fp = codecs.open(str(target), "wb", "utf-8") \
				 if not hasattr(target, "write") else target

			fp.write("# NgramProfile generated at %s\n" % time.time())

			lst = list()
			sublist = list()
			for i in xrange(self.minLength, self.maxLength + 1):
				for e in self.ngrams.values():
					if len(e.seq) == i:
						sublist.append(e)

				sublist = sorted(sublist)
				if len(sublist) > self.MAX_SIZE:
					sublist = sublist[:self.MAX_SIZE]

				lst.extend(sublist)
				sublist = []
			
			for e in lst:
				e.write(fp)
				fp.write(" %s\n" % e.count)
			fp.flush()
		finally:
			if close and fp:
				fp.close()

	@classmethod
	def create(cls, name, source, encoding="utf-8"):
		newProfile = LanguageProfilerBuilder(name)
		fp = open(str(source), "r") if not hasattr(source, "read") else source
		try:
			reader = codecs.getreader(encoding)(fp)
			text = reader.read()
		finally:
			fp.close()
		newProfile.analyze(text)
		return newProfile
