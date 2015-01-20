#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

import unittest

from nti.utils.sets import OrderedSet

class TestSets(unittest.TestCase):

	def test_ordered_sets(self):
		s = OrderedSet('abracadaba')
		t = OrderedSet('simsalabim')
		result = (s | t)
		assert_that(result, has_property('items', is_([u'a', u'b', u'r', u'c', u'd', u's', u'i', u'm', u'l'])))
		
		result = (s & t)
		assert_that(result, has_length(2))
		assert_that(result, has_property('items', is_([u'a', u'b'])))
		assert_that(result, has_item('a'))
		assert_that(result, has_item('b'))
		assert_that(result, does_not(has_item('c')))
		
		result.append('b')
		assert_that(result, has_length(2))
		
		result = (s - t)
		assert_that(result, has_property('items', is_([u'r', u'c', u'd'])))

		l = list(result)
		assert_that(l, is_([u'r', u'c', u'd']))