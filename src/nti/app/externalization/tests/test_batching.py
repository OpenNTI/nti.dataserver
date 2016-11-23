#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

import fudge

from unittest import TestCase

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.testing.request_response import DummyRequest

class TestBatching(TestCase):

	def setUp(self):
		self.request = DummyRequest()
		self.batching = BatchingUtilsMixin()
		self.batching.request = self.request

	def _set_batch_start_params(self, batch_size, batch_start):
		self.request.GET['batchSize'] = str(batch_size)
		self.request.GET['batchStart'] = str(batch_start)

	@fudge.patch('pyramid.url.URLMethodsMixin.current_route_path')
	def test_batch_list(self, mock_route):
		mock_route.is_callable().returns('/path/')
		do_batch = self.batching._BatchingUtilsMixin__batch_result_list

		# Basic batch
		result = {}
		result_list = range(50)
		batch_start = 0
		batch_size = 10
		# Don't remember what this is for...
		# -> A buffer to ensure we have a batch_next link
		number_items_needed = batch_size + batch_start + 2
		batched_results = do_batch(result, result_list,
									batch_start, batch_size,
									number_items_needed)

		assert_that(list(batched_results), is_(result_list[0:10]))

		# Next batch
		batch_start += 10
		number_items_needed = batch_size + batch_start + 2
		batched_results = do_batch(result, result_list,
									batch_start, batch_size,
									number_items_needed)

		assert_that(list(batched_results), is_(result_list[10:20]))

		# Outside of list gives us nothing
		batch_start = 50
		batched_results = do_batch(result, result_list,
									batch_start, batch_size,
									number_items_needed)

		assert_that(list(batched_results), has_length(0))

	@fudge.patch('pyramid.url.URLMethodsMixin.current_route_path')
	def test_batch_around(self, mock_route):
		mock_route.is_callable().returns('/path/')
		do_batch = self.batching._batch_on_item

		result_list = range(50)
		target_number = 30
		test_func = lambda x: x == target_number
		batch_start = 0
		batch_size = 10
		self._set_batch_start_params(batch_size, batch_start)

		# Batch around
		do_batch(result_list, test_func)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('24'))

		# Batch around (containing)
		do_batch(result_list, test_func, batch_containing=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('30'))

		# Batch around (after)
		do_batch(result_list, test_func, batch_after=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('31'))

		# Batch around (before)
		do_batch(result_list, test_func, batch_before=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('20'))

		# ## Front boundary condition
		target_number = 0

		# Batch around
		do_batch(result_list, test_func)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('0'))

		# Batch around (containing)
		do_batch(result_list, test_func, batch_containing=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('0'))

		# Batch around (after)
		do_batch(result_list, test_func, batch_after=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('1'))

		# Batch around (before)
		do_batch(result_list, test_func, batch_before=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('50'))

		# Back boundary condition
		target_number = 49

		# Batch around
		do_batch(result_list, test_func)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('43'))

		# Batch around (containing)
		do_batch(result_list, test_func, batch_containing=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('40'))

		# Batch around (after)
		do_batch(result_list, test_func, batch_after=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('50'))

		# Batch around (before)
		do_batch(result_list, test_func, batch_before=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('39'))

		# ## Non-existent
		target_number = 50

		# Batch around
		do_batch(result_list, test_func)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('50'))

		# Batch around (containing)
		do_batch(result_list, test_func, batch_containing=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('50'))

		# Batch around (after)
		do_batch(result_list, test_func, batch_after=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('50'))

		# Batch around (before)
		do_batch(result_list, test_func, batch_before=True)
		calc_batch_start = self.request.params.get('batchStart')
		assert_that(calc_batch_start, is_('50'))

		# ## Small batch before; reset since batchSize toggles
		self._set_batch_start_params(batch_size, batch_start)
		target_number = 1
		do_batch(result_list, test_func, batch_before=True)
		calc_batch_start = self.request.params.get('batchStart')
		calc_batch_size = self.request.params.get('batchSize')
		assert_that(calc_batch_start, is_('0'))
		assert_that(calc_batch_size, is_('1'))

		self._set_batch_start_params(batch_size, batch_start)
		target_number = 9
		do_batch(result_list, test_func, batch_before=True)
		calc_batch_start = self.request.params.get('batchStart')
		calc_batch_size = self.request.params.get('batchSize')
		assert_that(calc_batch_start, is_('0'))
		assert_that(calc_batch_size, is_('9'))

		self._set_batch_start_params(batch_size, batch_start)
		target_number = 10
		do_batch(result_list, test_func, batch_before=True)
		calc_batch_start = self.request.params.get('batchStart')
		calc_batch_size = self.request.params.get('batchSize')
		assert_that(calc_batch_start, is_('0'))
		assert_that(calc_batch_size, is_('10'))
