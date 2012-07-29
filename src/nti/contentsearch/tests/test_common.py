import os
import json
import unittest
import collections
from datetime import datetime

from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch._content_utils import get_content

from nti.contentsearch.common import echo
from nti.contentsearch.common import epoch_time
from nti.contentsearch.common import get_datetime
from nti.contentsearch.common import get_keywords
from nti.contentsearch.common import word_content_highlight
from nti.contentsearch.common import ngram_content_highlight
from nti.contentsearch.common import merge_search_results
from nti.contentsearch.common import merge_suggest_results
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch.common import empty_suggest_and_search_result

from hamcrest import (assert_that, has_length, is_, less_than_or_equal_to, has_entry)

class TestCommon(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):	
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)

	def test_echo(self):
		assert_that(echo(None), is_(''))
		assert_that(echo(''), is_(''))
		assert_that(echo('None'), is_('None'))

	def test_epoch_time(self):
		d = datetime.fromordinal(730920)
		assert_that(epoch_time(d), is_(1015826400.0) )
		assert_that(epoch_time(None), is_(0))

	def test_get_datetime(self):
		f = 1321391468.411328
		s = '1321391468.411328'
		assert_that(get_datetime(f), is_(get_datetime(s)))
		assert_that(datetime.now(), less_than_or_equal_to(get_datetime()))

	def test_get_keywords(self):
		assert_that(get_keywords(None), is_(''))
		assert_that(get_keywords(''), is_(''))
		assert_that(get_keywords(('Zanpakuto', 'Zangetsu')), is_('Zanpakuto,Zangetsu'))

	def test_word_content_highlight(self):
		text = unicode(get_content("""
			An orange-haired high school student, Ichigo becomes a "substitute Shinigami (Soul Reaper)"
			after unintentionally absorbing most of Rukia Kuchiki's powers"""))
		
		assert_that( word_content_highlight('ichigo', text), 
				is_('An orange-haired high school student ICHIGO becomes a substitute Shinigami Soul Reaper after unintentionally'))
		
		assert_that(word_content_highlight('ichigo', text, surround=5), is_('ICHIGO becomes'))
		
		assert_that(word_content_highlight('shinigami', text, maxchars=10), 
					is_('high school student Ichigo becomes a substitute SHINIGAMI Soul'))
		
		assert_that(word_content_highlight('rukia', text, maxchars=10, surround=1), is_('RUKIA'))

	def test_ngram_content_highlight(self):
		text = unicode(get_content('All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'))
		
		assert_that(ngram_content_highlight('strike', text), is_('STRIKE now and Become my Blade'))
		assert_that(ngram_content_highlight('str', text), is_('STRike now and Become my Blade'))
		
		assert_that(ngram_content_highlight('Lightning', text, surround=5), is_('LIGHTNING Strike now and Become my Blade'))
		
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
