#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from string import hexdigits, letters

from nti.folder.lazy import LazyCat
from nti.folder.lazy import LazyMap
from nti.folder.lazy import LazyValues

from nti.folder.tests import SharedConfiguringTestLayer

class BaseSequenceTest(object):

	def _compare(self, lseq, seq):
		assert_that(lseq, has_length(len(seq)))
		assert_that(list(lseq), is_(seq))

	def test_actual_result_count(self):
		lcat = self._createLSeq(range(10))
		assert_that(lcat, has_length(10))
		assert_that(lcat.actual_result_count, is_(10))

		lcat.actual_result_count = 20
		assert_that(lcat, has_length(10))
		assert_that(lcat, has_property('actual_result_count', is_(20)))

class TestLazyCat(unittest.TestCase, BaseSequenceTest):

	layer = SharedConfiguringTestLayer

	def _createLSeq(self, *sequences):
		return LazyCat(sequences)

	def _createLValues(self, seq):
		return LazyValues(seq)

	def test_empty(self):
		lcat = self._createLSeq([])
		self._compare(lcat, [])
		assert_that(lcat, has_property('actual_result_count', is_(0)))

	def test_repr(self):
		lcat = self._createLSeq([0, 1])
		assert_that(repr(lcat), is_(repr([0, 1])))

	def test_init_single(self):
		seq = range(10)
		lcat = self._createLSeq(seq)
		self._compare(lcat, seq)
		assert_that(lcat, has_property('actual_result_count', is_(10)))

	def test_add(self):
		seq1 = range(10)
		seq2 = range(10, 20)
		lcat1 = self._createLSeq(seq1)
		lcat2 = self._createLSeq(seq2)
		lcat = lcat1 + lcat2
		self._compare(lcat, range(20))
		assert_that(lcat, has_property('actual_result_count', is_(20)))

	def test_add_after_getitem(self):
		seq1 = range(10)
		seq2 = range(10, 20)
		lcat1 = self._createLSeq(seq1)
		lcat2 = self._createLSeq(seq2)
		# turning lcat1 into a list will flatten it into _data and remove _seq
		list(lcat1)
		lcat = lcat1 + lcat2
		self._compare(lcat, range(20))
		assert_that(lcat, has_property('actual_result_count', is_(20)))

	def test_init_multiple(self):
		seq1 = range(10)
		seq2 = list(hexdigits)
		seq3 = list(letters)
		lcat = self._createLSeq(seq1, seq2, seq3)
		self._compare(lcat, seq1 + seq2 + seq3)

	def test_init_nested(self):
		seq1 = range(10)
		seq2 = list(hexdigits)
		seq3 = list(letters)
		lcat = apply(self._createLSeq,
					 [self._createLSeq(seq) for seq in (seq1, seq2, seq3)])
		self._compare(lcat, seq1 + seq2 + seq3)

	def test_slicing(self):
		seq1 = range(10)
		seq2 = list(hexdigits)
		seq3 = list(letters)
		lcat = apply(self._createLSeq,
					 [self._createLSeq(seq) for seq in (seq1, seq2, seq3)])
		self._compare(lcat[5:-5], seq1[5:] + seq2 + seq3[:-5])

	def test_length(self):
		# Unaccessed length
		lcat = self._createLSeq(range(10))
		assert_that(lcat, has_length(10))
		assert_that(lcat, has_property('actual_result_count', is_(10)))

		# Accessed in the middle
		lcat = self._createLSeq(range(10))
		lcat[4]
		assert_that(lcat, has_length(10))
		assert_that(lcat, has_property('actual_result_count', is_(10)))

		# Accessed after the lcat is accessed over the whole range
		lcat = self._createLSeq(range(10))
		lcat[:]
		assert_that(lcat, has_length(10))
		assert_that(lcat, has_property('actual_result_count', is_(10)))

	def test_actual_result_count(self):
		# specify up-front
		lcat = self._createLSeq(range(10))
		lcat.actual_result_count = 100

		assert_that(lcat, has_length(10))
		assert_that(lcat, has_property('actual_result_count', is_(100)))

		lvalues = self._createLValues([])
		assert_that(lvalues, has_length(0))
		assert_that(lvalues, has_property('actual_result_count', is_(0)))

		combined = lvalues + lcat
		assert_that(combined, has_length(10))
		assert_that(combined, has_property('actual_result_count', is_(100)))

		combined.actual_result_count = 5
		assert_that(combined, has_property('actual_result_count', is_(5)))

class TestLazyMap(TestLazyCat):

	def _createLSeq(self, *seq):
		return self._createLMap(lambda x: x, *seq)

	def _createLMap(self, mapfunc, *seq):
		totalseq = []
		for s in seq:
			totalseq.extend(s)
		return LazyMap(mapfunc, totalseq)

	def test_map(self):
		seq1 = range(10)
		seq2 = list(hexdigits)
		seq3 = list(letters)
		function = lambda x: str(x).lower()
		lmap = self._createLMap(function, seq1, seq2, seq3)
		self._compare(lmap, [str(x).lower() for x in (seq1 + seq2 + seq3)])

	def testMapFuncIsOnlyCalledAsNecessary(self):
		seq = range(10)
		count = [0]  # closure only works with list, and `nonlocal` in py3
		def func(x):
			count[0] += 1
			return x
		lmap = self._createLMap(func, seq)
		assert_that(lmap[5], is_(5))
		assert_that(count[0], is_(1))
