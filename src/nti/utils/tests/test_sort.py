#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest

from ..sort import isorted

from hamcrest import (assert_that, is_)

class TestSort(unittest.TestCase):

	def test_istored(self):
		l =  [2, 1, 5, 3, 7, 9, 4]
		r = list(isorted(l))
		assert_that(r, is_([1, 2, 3, 4, 5, 7, 9]))
		
		comparator = lambda x,y : x > y
		r = list(isorted(l, comparator))
		assert_that(r, is_([9, 7, 5, 4, 3, 2, 1]))
