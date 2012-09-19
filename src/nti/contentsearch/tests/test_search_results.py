import os
import json
import unittest

from zope import component

from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch._search_query import QueryObject
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._search_results import empty_search_results
from nti.contentsearch._search_results import empty_suggest_results
from nti.contentsearch._search_results import merge_search_results
from nti.contentsearch._search_results import merge_suggest_results
from nti.contentsearch._search_results import empty_suggest_and_search_results

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch.tests import domain as domain_words

from hamcrest import (assert_that, has_length, is_, is_not, has_item)

class TestSearchResults(ConfiguringTestBase):

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

	def test_empty_search_results(self):
		d = empty_search_results(QueryObject.create("myQuery"))
		assert_that(d, has_length(0))
		assert_that(d.hits, is_([]))

	def test_empty_suggest_result(self):
		d = empty_suggest_results(QueryObject.create("myQuery"))
		assert_that(d, has_length(0))
		assert_that(d.suggestions, has_length(0) )

	def test_empty_suggest_and_search_result(self):
		d = empty_suggest_and_search_results(QueryObject.create("myQuery"))
		assert_that(d, has_length(0))
		assert_that(d.hits, is_([]))
		assert_that(d.suggestions, has_length(0) )

	def test_merge_search_results(self):
		
		a = empty_search_results(QueryObject.create("myQuery"))
		a.prop1 = 'value0'
		
		b = empty_search_results(QueryObject.create("myQuery"))
		b.prop1 = 'value1'
		b.prop2 = 'value2'
		
		containerid = make_ntiid(nttype='bleach', specific='manga')
		for x, cmd in enumerate(zanpakuto_commands):
			note = Note()
			note.body = [unicode(cmd)]
			note.creator = 'nt@nti.com'
			note.containerId = containerid
			result = b if x % 2 == 0 else a
			result.add(note)
		
		assert_that(a.prop1, is_('value0'))
		
		offset = len(a)
		a = merge_search_results(a, b)
		assert_that(a, has_length(len(zanpakuto_commands)))
		for x, note in enumerate(b):
			assert_that(note, is_(a[offset+x]))
			
		assert_that(a.prop1, is_('value1'))
		assert_that(a.prop2, is_('value2'))

	def test_merge_suggest_results(self):
		
		a = empty_suggest_results(QueryObject.create("myQuery"))
		a.prop1 = 'value0'
		
		b = empty_suggest_results(QueryObject.create("myQuery"))
		b.prop1 = 'value1'
		b.prop2 = 'value2'
		
		a.add(['a'])
		b.add(['b','c'])
		a = merge_suggest_results(a, b)
		assert_that(a, has_length(3))
		
		for x in ('a', 'b', 'c'):
			assert_that(a, has_item(x))
			
		assert_that(a.prop1, is_('value1'))
		assert_that(a.prop2, is_('value2'))

if __name__ == '__main__':
	unittest.main()
