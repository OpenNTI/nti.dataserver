#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from .. import maps

from hamcrest import (assert_that, has_length, is_)

class TestUtils(unittest.TestCase):

	def test_case_insensitive_dict(self):
		d1 = maps.CaseInsensitiveDict(ONE=1, two=2)
		d2 = maps.CaseInsensitiveDict({'One':1, 'Two':2})
		for m in (d1, d2):
			assert_that(m, has_length(2))
			assert_that(m['OnE'], is_(1))
			assert_that(m['one'], is_(1))
			assert_that(m['TWO'], is_(2))

