#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from .._redis_indexstore import sort_messages
from .._redis_indexstore import (ADD_OPERATION, UPDATE_OPERATION, DELETE_OPERATION)

from hamcrest import (assert_that, is_)

class TestRedisIndexStore(unittest.TestCase):

	def test_sort_messages(self):
		msgs = [(DELETE_OPERATION, 1, 'a'), (ADD_OPERATION, 1, 'a'), (UPDATE_OPERATION, 1, 'a')]
		sorted_list = sort_messages(msgs)
		exp = [(ADD_OPERATION, 1, 'a'), (UPDATE_OPERATION, 1, 'a'), (DELETE_OPERATION, 1, 'a')]
		assert_that(sorted_list, is_(exp))

		msgs = [(DELETE_OPERATION, 1, 'z'), (ADD_OPERATION, 1, 'x'), (UPDATE_OPERATION, 1, 'y')]
		sorted_list = sort_messages(msgs)
		exp = [(ADD_OPERATION, 1, 'x'), (UPDATE_OPERATION, 1, 'y'), (DELETE_OPERATION, 1, 'z')]
		assert_that(sorted_list, is_(exp))

		msgs = [(DELETE_OPERATION, 5, 'a'), (ADD_OPERATION, 2, 'a'), (UPDATE_OPERATION, 7, 'a')]
		sorted_list = sort_messages(msgs)
		exp = [(ADD_OPERATION, 2, 'a'), (DELETE_OPERATION, 5, 'a'), (UPDATE_OPERATION, 7, 'a')]
		assert_that(sorted_list, is_(exp))

		msgs = [(UPDATE_OPERATION, 1, 'a'), (UPDATE_OPERATION, 1, 'a'), (DELETE_OPERATION, 1, 'a')]
		sorted_list = sort_messages(msgs)
		assert_that(sorted_list, is_(msgs))
