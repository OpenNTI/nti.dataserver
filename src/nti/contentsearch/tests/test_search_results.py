import os
import json
import unittest
import collections

from zope import component

from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch._search_query import QueryObject
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._search_results import empty_search_result
from nti.contentsearch._search_results import empty_suggest_result
from nti.contentsearch._search_results import merge_search_results
from nti.contentsearch._search_results import merge_suggest_results
from nti.contentsearch._search_results import empty_suggest_and_search_result
from nti.contentsearch.common import LAST_MODIFIED, QUERY, ITEMS, HIT_COUNT, SUGGESTIONS

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch.tests import domain as domain_words

from hamcrest import (assert_that, has_length, is_, is_not, has_entry, has_item)

class TestCommon(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):	
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)
		
	def test_search_results(self):
		qo = QueryObject.create("test")
		sr = component.getUtility(search_interfaces.ISearchResultsCreator)(qo)
		assert_that(sr, is_not(None))
		assert_that(search_interfaces.ISearchResults.providedBy(sr), is_(True))
		
		notes = []
		containerid = make_ntiid(nttype='bleach', specific='manga')
		for cmd in zanpakuto_commands:
			note = Note()
			note.body = [unicode(cmd)]
			note.creator = 'nt@nti.com'
			note.containerId = containerid
			notes.append(note)
			
		sr.add(notes)
		assert_that(len(sr), is_(len(notes)))
		for x, note in enumerate(notes):
			assert_that(note, is_(sr[x]))
			
		note = Note()
		note.body = [u'test']
		note.creator = 'nt@nti.com'
		note.containerId = containerid
		sr.add(note)
		
		count = 0
		for n in sr.hits:
			assert_that(n, is_not(None))
			count = count + 1
			
		expected = len(notes) + 1
		assert_that(count, is_(expected))
		
		sr.add(1)
		sr.add('no to be added')
		assert_that(sr, has_length(expected))
	
	def test_suggest_results(self):
		qo = QueryObject.create("test")
		sr = component.getUtility(search_interfaces.ISuggestResultsCreator)(qo)
		assert_that(sr, is_not(None))
		assert_that(search_interfaces.ISuggestResults.providedBy(sr), is_(True))
		
		sr.add_suggestions(domain_words)
		
		assert_that(sr, has_length(len(domain_words)))
		for word in domain_words:
			assert_that(sr.hits, has_item(word))
			
		sr.add('ichigo')
		expected = len(domain_words) + 1
		assert_that(sr, has_length(expected))
		
		count = 0
		for n in sr.hits:
			count = count + 1
			assert_that(n, is_not(None))
			
		assert_that(count, is_(expected))
		
		sr.add(1) ## should not add
		sr.add(Note()) ## should not add
		assert_that(sr, has_length(expected))
			
	def test_suggest_and_search_results(self):
		qo = QueryObject.create("test")
		sr = component.getUtility(search_interfaces.ISuggestAndSearchResultsCreator)(qo)
		assert_that(sr, is_not(None))
		assert_that(search_interfaces.ISuggestAndSearchResults.providedBy(sr), is_(True))
		
		sr.add_suggestions(domain_words)
		assert_that(sr.suggestions, has_length(len(domain_words)))
		for word in domain_words:
			assert_that(sr.suggestions, has_item(word))
			
		notes = []
		containerid = make_ntiid(nttype='bleach', specific='manga')
		for cmd in zanpakuto_commands:
			note = Note()
			note.body = [unicode(cmd)]
			note.creator = 'nt@nti.com'
			note.containerId = containerid
			notes.append(note)
		sr.add(notes)
		assert_that(sr, has_length(len(notes)))
		
	def _check_empty(self, d, query):
		assert_that(isinstance(d, collections.Mapping), is_(True))
		assert_that(d, has_entry(QUERY, query))
		assert_that(d, has_entry(HIT_COUNT, 0))
		assert_that(d, has_entry(LAST_MODIFIED, 0))

	def test_empty_search_result(self):
		d = empty_search_result('myQuery')
		self._check_empty(d, 'myQuery')
		assert_that(d, has_entry(ITEMS,{}))

	def test_empty_suggest_result(self):
		d = empty_suggest_result('myQuery')
		self._check_empty(d, 'myQuery')
		assert_that( d[ITEMS], has_length(0) )

	def test_empty_suggest_and_search_result(self):
		d = empty_suggest_and_search_result('myQuery')
		self._check_empty(d, 'myQuery')
		assert_that(d, has_entry(ITEMS,{}))
		assert_that(d, has_entry(SUGGESTIONS, []))

	def test_merge_search_results(self):
		a = {LAST_MODIFIED: 1, ITEMS:{'a':1}}
		b = {LAST_MODIFIED: 2, ITEMS:{'b':2}}
		m = merge_search_results(a, b)
		
		assert_that(m, has_entry(LAST_MODIFIED, 2))
		assert_that(m, has_entry(ITEMS, {'a':1, 'b':2}))
		assert_that(m, has_entry(HIT_COUNT, 2))
	
		a = {LAST_MODIFIED: 1, ITEMS:{'a':1}}
		b = {ITEMS:{'b':2}}
		m = merge_search_results(a, b)
		assert_that(m, has_entry(LAST_MODIFIED, 1))

		a = {ITEMS:{'a':1}}
		b = {LAST_MODIFIED: 3, ITEMS:{'b':2}}
		m = merge_search_results(a, b)
		assert_that(m, has_entry(LAST_MODIFIED, 3))

		a = None
		b = {LAST_MODIFIED: 3, ITEMS:{'b':2}}
		m = merge_search_results(a, b)
		assert_that(m, is_(b))

		a = {LAST_MODIFIED: 3, ITEMS:{'b':2}}
		b = None
		m = merge_search_results(a, b)
		assert_that(m, is_(a))

		m = merge_search_results(None, None)
		assert_that(m, is_(None))

	def test_merge_suggest_results(self):
		a = {LAST_MODIFIED: 4, ITEMS:['a']}
		b = {LAST_MODIFIED: 2, ITEMS:['b','c']}
		m = merge_suggest_results(a, b)
		
		assert_that(m, has_entry(LAST_MODIFIED, 4))
		assert_that(m, has_entry(ITEMS, ['a','c', 'b']))
		assert_that(m, has_entry(HIT_COUNT, 3))

		a = {LAST_MODIFIED: 1, ITEMS:['a']}
		b = {ITEMS:['b']}
		m = merge_suggest_results(a, b)
		assert_that(m, has_entry(LAST_MODIFIED, 1))
		assert_that(m, has_entry(ITEMS, ['a','b']))

		a = {ITEMS:['a']}
		b = {LAST_MODIFIED: 3, ITEMS:['b']}
		m = merge_suggest_results(a, b)
		self.assertEqual(3, m[LAST_MODIFIED])

		a = None
		b = {LAST_MODIFIED: 3, ITEMS:['b']}
		m = merge_suggest_results(a, b)
		assert_that(m, is_(b))

		a = {LAST_MODIFIED: 3, ITEMS:['c']}
		b = None
		m = merge_suggest_results(a, b)
		assert_that(m, is_(a))

		m = merge_suggest_results(None, None)
		assert_that(m, is_(None))

if __name__ == '__main__':
	unittest.main()
