#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

import unittest
import itertools

from nti.utils.iterables import IterableWrapper

class TestIterables(unittest.TestCase):

	def test_wrapper(self):
		a = range(1, 6)
		b = range(6, 11)
		w = IterableWrapper(itertools.chain(a, b), 10)
		assert_that(w, has_length(10))
		assert_that(list(w), has_length(10))

		w = IterableWrapper(itertools.chain(a, b), 10)
		assert_that(w[4], is_(5))

		w = IterableWrapper(itertools.chain(a, b), 10)
		assert_that(w[4:6], is_([5, 6]))
