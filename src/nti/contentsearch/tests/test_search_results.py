import os
import json
import unittest
import collections

from nti.contentsearch.tests import ConfiguringTestBase

from nti.contentsearch._search_results import merge_search_results
from nti.contentsearch._search_results import merge_suggest_results
from nti.contentsearch._search_results import empty_search_result
from nti.contentsearch._search_results import empty_suggest_result
from nti.contentsearch._search_results import empty_suggest_and_search_result

from hamcrest import (assert_that, has_length, is_, has_entry)

class TestCommon(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):	
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)
		
	def _check_empty(self, d, query):
		assert_that(isinstance(d, collections.Mapping), is_(True))
		assert_that(d, has_entry('Query', query))
		assert_that(d, has_entry('Hit Count', 0))
		assert_that(d, has_entry('Last Modified', 0))

	def test_empty_search_result(self):
		d = empty_search_result('myQuery')
		self._check_empty(d, 'myQuery')
		assert_that(d, has_entry('Items',{}))

	def test_empty_suggest_result(self):
		d = empty_suggest_result('myQuery')
		self._check_empty(d, 'myQuery')
		assert_that( d['Items'], has_length(0) )

	def test_empty_suggest_and_search_result(self):
		d = empty_suggest_and_search_result('myQuery')
		self._check_empty(d, 'myQuery')
		assert_that(d, has_entry('Items',{}))
		assert_that(d, has_entry('Suggestions', []))

	def test_merge_search_results(self):
		a = {'Last Modified': 1, 'Items':{'a':1}}
		b = {'Last Modified': 2, 'Items':{'b':2}}
		m = merge_search_results(a, b)
		
		assert_that(m, has_entry('Last Modified', 2))
		assert_that(m, has_entry('Items', {'a':1, 'b':2}))
		assert_that(m, has_entry('Hit Count', 2))
	
		a = {'Last Modified': 1, 'Items':{'a':1}}
		b = {'Items':{'b':2}}
		m = merge_search_results(a, b)
		assert_that(m, has_entry('Last Modified', 1))

		a = {'Items':{'a':1}}
		b = {'Last Modified': 3, 'Items':{'b':2}}
		m = merge_search_results(a, b)
		assert_that(m, has_entry('Last Modified', 3))

		a = None
		b = {'Last Modified': 3, 'Items':{'b':2}}
		m = merge_search_results(a, b)
		assert_that(m, is_(b))

		a = {'Last Modified': 3, 'Items':{'b':2}}
		b = None
		m = merge_search_results(a, b)
		assert_that(m, is_(a))

		m = merge_search_results(None, None)
		assert_that(m, is_(None))

	def test_merge_suggest_results(self):
		a = {'Last Modified': 4, 'Items':['a']}
		b = {'Last Modified': 2, 'Items':['b','c']}
		m = merge_suggest_results(a, b)
		
		assert_that(m, has_entry('Last Modified', 4))
		assert_that(m, has_entry('Items', ['a','c', 'b']))
		assert_that(m, has_entry('Hit Count', 3))

		a = {'Last Modified': 1, 'Items':['a']}
		b = {'Items':['b']}
		m = merge_suggest_results(a, b)
		assert_that(m, has_entry('Last Modified', 1))
		assert_that(m, has_entry('Items', ['a','b']))

		a = {'Items':['a']}
		b = {'Last Modified': 3, 'Items':['b']}
		m = merge_suggest_results(a, b)
		self.assertEqual(3, m['Last Modified'])

		a = None
		b = {'Last Modified': 3, 'Items':['b']}
		m = merge_suggest_results(a, b)
		assert_that(m, is_(b))

		a = {'Last Modified': 3, 'Items':['c']}
		b = None
		m = merge_suggest_results(a, b)
		assert_that(m, is_(a))

		m = merge_suggest_results(None, None)
		assert_that(m, is_(None))

if __name__ == '__main__':
	unittest.main()
