#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from .. import from_delimited

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_length)

class TestUtils(ConfiguringTestBase):

	def test_from_delimited(self):
		a = ['tag:nextthought.com,2011-10:CMU-HTML-04630_main.04_630:_computer_science_for_practicing_engineers',
			 'tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.cosmetology']
		a = ' '.join(a)
		items = from_delimited(a)
		assert_that(items, has_length(2))

		a = 'tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.cosmetology'
		items = from_delimited(a)
		assert_that(items, has_length(1))
		assert_that(items[0], is_(a))
