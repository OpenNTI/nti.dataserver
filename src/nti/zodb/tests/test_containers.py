#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_entry
from hamcrest import assert_that

import unittest

import BTrees

from nti.common.time import time_to_64bit_int

family = BTrees.family64

class TestContainer(unittest.TestCase):

	def test_negative_values_in_btree(self):
		bt = family.IO.BTree()

		for i in xrange(-1, -10000, -5):
			bt[time_to_64bit_int(i)] = str(i)

		for i in xrange(-1, -10000, -5):
			assert_that( bt, has_entry( time_to_64bit_int(i), str(i)))


	def test_positive_values_in_btree(self):
		bt = family.IO.BTree()

		for i in xrange(1, 10000, 10):
			bt[time_to_64bit_int(i)] = str(i)


		for i in xrange(1, 10000, 10):
			assert_that( bt, has_entry( time_to_64bit_int(i), str(i)))
