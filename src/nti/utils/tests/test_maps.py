#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from .. import maps

from hamcrest import (assert_that, is_, has_length)

class TestUtils(unittest.TestCase):

	def test_case_insensitive_dict(self):
		d = maps.CaseInsensitiveDict(ONE=1, two=2)
		assert_that(d, has_length(2))
		assert_that(d['OnE'], is_(1))
		assert_that(d['one'], is_(1))
		assert_that(d['TWO'], is_(2))


