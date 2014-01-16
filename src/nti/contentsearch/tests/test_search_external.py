#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from zope import component

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from ..search_results import IndexHit
from ..search_query import QueryObject
from .. import interfaces as search_interfaces
from ..constants import (LAST_MODIFIED, HIT_COUNT, ITEMS, QUERY, SUGGESTIONS, SCORE, HIT_META_DATA, TYPE_COUNT)

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import zanpakuto_commands
from . import ConfiguringTestBase
from . import domain as domain_words

from hamcrest import (assert_that, has_entry, has_key, has_length, greater_than_or_equal_to, is_, has_property)

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
	def test_externalize_search_results(self):
		qo = QueryObject.create("wind")
		containerId = make_ntiid(nttype='bleach', specific='manga')
		searchResults = component.getUtility(search_interfaces.ISearchResultsCreator)(qo)

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
		assert_that(eo, has_key(HIT_META_DATA))
		md = eo[HIT_META_DATA]
		assert_that(md, has_key(TYPE_COUNT))
		tc = md[TYPE_COUNT]
		assert_that(tc, has_entry('note', len(notes)))

	@WithMockDSTrans
	def test_externalize_suggest_results(self):
		qo = QueryObject.create("bravo")
		sr = component.getUtility(search_interfaces.ISuggestResultsCreator)(qo)
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
	def test_externalize_search_suggest_results(self):
		qo = QueryObject.create("theotokos")
		searchResults = component.getUtility(search_interfaces.ISuggestAndSearchResultsCreator)(qo)

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

	@WithMockDSTrans
	def test_search_query(self):
		qo = QueryObject.create("sode no shirayuki", sortOn='relevance', searchOn=('note',))
		# externalize
		eo = toExternalObject(qo)
		assert_that(eo, has_entry(u'Class', u'SearchQuery'))
		assert_that(eo, has_entry(u'MimeType', u'application/vnd.nextthought.search.query'))
		assert_that(eo, has_entry(u'sortOn', u'relevance'))
		assert_that(eo, has_entry(u'term', u'sode no shirayuki'))
		assert_that(eo, has_entry(u'searchOn', is_([u'note'])))
		# internalize
		factory = find_factory_for(eo)
		new_query = factory()
		update_from_external_object(new_query, eo)
		assert_that(new_query, has_property('term', 'sode no shirayuki'))
		assert_that(new_query, has_property('sortOn', 'relevance'))
		assert_that(new_query, has_property('searchOn', is_(['note'])))

	@WithMockDSTrans
	def test_index_hit(self):
		hit = IndexHit(1L, 1.0)
		# externalize
		eo = toExternalObject(hit)
		assert_that(eo, has_entry(u'Class', u'IndexHit'))
		assert_that(eo, has_entry(u'MimeType', u'application/vnd.nextthought.search.indexhit'))
		assert_that(eo, has_entry(u'Ref', 1L))
		assert_that(eo, has_entry(u'Score', 1.0))
		# internalize
		factory = find_factory_for(eo)
		new_index = factory()
		update_from_external_object(new_index, eo)
		assert_that(hit, new_index)

		# test w/ a note
		note = Note()
		note.body = [unicode('rubby haddock')]
		hit = IndexHit(note, 0.5)
		eo = toExternalObject(hit)
		assert_that(eo, has_entry(u'Class', u'IndexHit'))
		assert_that(eo, has_entry(u'MimeType', u'application/vnd.nextthought.search.indexhit'))
		assert_that(eo, has_entry(u'Ref', has_entry('body', is_([u'rubby haddock']))))
		assert_that(eo, has_entry(u'Score', 0.5))
		# internalize
		factory = find_factory_for(eo)
		new_index = factory()
		update_from_external_object(new_index, eo)
		assert_that(hit, new_index)

