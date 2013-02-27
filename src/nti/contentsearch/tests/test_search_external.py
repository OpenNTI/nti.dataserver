#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import unittest

from zope import component

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject

from nti.contentsearch._search_query import QueryObject
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._search_highlights import WORD_HIGHLIGHT
from nti.contentsearch.common import (LAST_MODIFIED, HIT_COUNT, ITEMS, QUERY, SUGGESTIONS, SCORE)
									
import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch.tests import domain as domain_words

from hamcrest import (assert_that, has_entry, has_key, has_length, greater_than_or_equal_to, is_)

class TestSearchExternal(ConfiguringTestBase):
			
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
	
	def _create_notes(self, username, containerId, commands=zanpakuto_commands):
		notes = []
		for cmd in commands:
			note = Note()
			note.body = [unicode(cmd)]
			note.creator =  username
			note.containerId = containerId
			notes.append(note)
		return notes
			
	@WithMockDSTrans
	def xtest_externalize_search_results(self):
		qo = QueryObject.create("wind")
		containerId = make_ntiid(nttype='bleach', specific='manga')	
		searchResults = component.getUtility(search_interfaces.ISearchResultsCreator)(qo)
		searchResults.highlight_type = WORD_HIGHLIGHT
		
		usr = self._create_user()
		notes = self._create_notes(usr.username, containerId)
		for note in notes:
			mock_dataserver.current_transaction.add(note)
			note = usr.addContainedObject( note )	
		searchResults.add(notes)
		
		eo = toExternalObject(searchResults)
		assert_that(eo, has_entry(QUERY, u'wind'))
		assert_that(eo, has_entry(HIT_COUNT, len(zanpakuto_commands)))
		assert_that(eo, has_key(LAST_MODIFIED))
		assert_that(eo[LAST_MODIFIED], greater_than_or_equal_to(0))
		assert_that(eo, has_key(ITEMS))
		assert_that(eo[ITEMS], has_length(len(zanpakuto_commands)))
		
	@WithMockDSTrans
	def xtest_externalize_suggest_results(self):
		qo = QueryObject.create("bravo")
		sr = component.getUtility(search_interfaces.ISuggestResultsCreator)(qo)
		sr.highlight_type = WORD_HIGHLIGHT
		sr.add_suggestions(domain_words)
		eo = toExternalObject(sr)
		assert_that(eo, has_entry(QUERY, u'bravo'))
		assert_that(eo, has_entry(HIT_COUNT, len(domain_words)))
		assert_that(eo, has_key(LAST_MODIFIED))
		assert_that(eo[LAST_MODIFIED], greater_than_or_equal_to(0))
		assert_that(eo, has_key(ITEMS))
		assert_that(eo[ITEMS], has_length(len(domain_words)))
		assert_that(eo[SUGGESTIONS], has_length(len(domain_words)))
		
	@WithMockDSTrans
	def xtest_externalize_search_suggest_results(self):
		qo = QueryObject.create("theotokos")
		searchResults = component.getUtility(search_interfaces.ISuggestAndSearchResultsCreator)(qo)
		searchResults.highlight_type = WORD_HIGHLIGHT
		
		suggestions = domain_words[:3]
		searchResults.add_suggestions(suggestions)
		
		usr = self._create_user()
		commands = zanpakuto_commands[:5]
		containerId = make_ntiid(nttype='bleach', specific='manga')	
		
		notes = self._create_notes(usr.username, containerId, commands)
		for note in notes:
			mock_dataserver.current_transaction.add(note)
			note = usr.addContainedObject( note )	
		searchResults.add(notes)
		
		eo = toExternalObject(searchResults)
		assert_that(eo, has_entry(QUERY, u'theotokos'))
		assert_that(eo, has_entry(HIT_COUNT, len(commands)))
		assert_that(eo, has_key(LAST_MODIFIED))
		assert_that(eo[LAST_MODIFIED], greater_than_or_equal_to(0))
		assert_that(eo, has_key(ITEMS))
		assert_that(eo[ITEMS], has_length(len(commands)))
		assert_that(eo[SUGGESTIONS], has_length(len(suggestions)))
		
	@WithMockDSTrans
	def test_search_results_sort_relevance(self):
		
		qo = QueryObject.create("sode no shirayuki", sortOn='relevance')
		containerId = make_ntiid(nttype='bleach', specific='manga')	
		searchResults = component.getUtility(search_interfaces.ISearchResultsCreator)(qo)
		searchResults.highlight_type = WORD_HIGHLIGHT
		
		usr = self._create_user()
		notes = self._create_notes(usr.username, containerId)
		for score, note in enumerate(notes):
			mock_dataserver.current_transaction.add(note)
			note = usr.addContainedObject( note )	
			searchResults.add((note, score+1))
		
		eo = toExternalObject(searchResults)
		assert_that(eo, has_entry(HIT_COUNT, len(zanpakuto_commands)))
		assert_that(eo, has_key(LAST_MODIFIED))
		assert_that(eo, has_entry(ITEMS, has_length(len(zanpakuto_commands))))
		items = eo[ITEMS]
		for idx, hit in enumerate(items):
			score = len(items) - idx
			assert_that(hit[SCORE], is_(score))
		
if __name__ == '__main__':
	unittest.main()
