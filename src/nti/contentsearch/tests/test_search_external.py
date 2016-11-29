#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import equal_to
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import greater_than_or_equal_to

import unittest

from zope import component

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.contentsearch.search_query import QueryObject
from nti.contentsearch.search_query import DateTimeRange
from nti.contentsearch import interfaces as search_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import domain as domain_words
from nti.contentsearch.tests import SharedConfiguringTestLayer

class TestSearchExternal(unittest.TestCase):

	layer = SharedConfiguringTestLayer

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
# 
# 	@WithMockDSTrans
# 	def test_externalize_search_results(self):
# 		qo = QueryObject.create("wind")
# 		qo.limit = 100
# 		containerId = make_ntiid(nttype='bleach', specific='manga')
# 		searchResults = component.getUtility(search_interfaces.ISearchResultsCreator)(qo)
# 
# 		usr = self._create_user()
# 		notes = self._create_notes(usr.username, containerId)
# 		for note in notes:
# 			mock_dataserver.current_transaction.add(note)
# 			note = usr.addContainedObject( note )
# 		searchResults.extend(notes)
# 		old_hits = list(searchResults.Hits)
# 
# 		eo = toExternalObject(searchResults)
# 		assert_that(eo, has_entry('Query', u'wind'))
# 		assert_that(eo, has_entry(HIT_COUNT, len(zanpakuto_commands)))
# 		assert_that(eo, has_key(LAST_MODIFIED))
# 		assert_that(eo[LAST_MODIFIED], greater_than_or_equal_to(0))
# 		assert_that(eo, has_key(ITEMS))
# 		assert_that(eo[ITEMS], has_length(len(zanpakuto_commands)))
# 		assert_that(eo, has_key(HIT_META_DATA))
# 		md = eo[HIT_META_DATA]
# 		assert_that(md, has_entry('TypeCount', has_entry('note', len(notes))))
# 
# 		# internalize
# 		factory = find_factory_for(eo)
# 		new_results = factory()
# 		update_from_external_object(new_results, eo)
# 
# 		assert_that(new_results, has_property('Query', is_not(none())))
# 		assert_that(new_results, has_property('Query', has_property('limit', is_(100))))
# 
# 		new_hits = list(new_results.Hits)
# 		assert_that(new_hits, has_length(len(old_hits)))
# 		assert_that(new_hits, equal_to(old_hits))
# 		for hit in new_hits:
# 			assert_that(hit, has_property('Query', is_(equal_to(new_results.Query))))
# 
# 	@WithMockDSTrans
# 	def test_externalize_suggest_results(self):
# 		qo = QueryObject.create("bravo")
# 		sr = component.getUtility(search_interfaces.ISuggestResultsCreator)(qo)
# 		sr.add_suggestions(domain_words)
# 		old_suggestions = list(sr.Suggestions)
# 		eo = toExternalObject(sr)
# 		assert_that(eo, has_entry('Query', u'bravo'))
# 		assert_that(eo, has_entry(HIT_COUNT, len(domain_words)))
# 		assert_that(eo, has_key(LAST_MODIFIED))
# 		assert_that(eo[LAST_MODIFIED], greater_than_or_equal_to(0))
# 		assert_that(eo, has_key(ITEMS))
# 		assert_that(eo[ITEMS], has_length(len(domain_words)))
# 
# 		# internalize
# 		factory = find_factory_for(eo)
# 		new_results = factory()
# 		update_from_external_object(new_results, eo)
# 		new_suggestions = list(new_results.Suggestions)
# 		assert_that(new_suggestions, has_length(len(old_suggestions)))
# 		assert_that(new_suggestions, equal_to(old_suggestions))
# 
# 	@WithMockDSTrans
# 	def test_search_query(self):
# 		creationTime = DateTimeRange(startTime=0, endTime=100)
# 		qo = QueryObject.create("sode no shirayuki", sortOn='relevance', searchOn=('note',),
# 								creationTime=creationTime, context={'theotokos':'Mater Dei'})
# 		# externalize
# 		eo = toExternalObject(qo)
# 		assert_that(eo, has_entry(u'Class', u'SearchQuery'))
# 		assert_that(eo, has_entry(u'MimeType', u'application/vnd.nextthought.search.query'))
# 		assert_that(eo, has_entry(u'sortOn', u'relevance'))
# 		assert_that(eo, has_entry(u'term', u'sode no shirayuki'))
# 		assert_that(eo, has_entry(u'searchOn', is_([u'note'])))
# 		assert_that(eo, has_entry(u'context', has_entry('theotokos','Mater Dei')))
# 		assert_that(eo, has_key(u'creationTime'))
# 		entry = eo['creationTime']
# 		assert_that(entry, has_entry(u'startTime', is_(0)))
# 		assert_that(entry, has_entry(u'endTime', is_(100)))
# 
# 		# internalize
# 		factory = find_factory_for(eo)
# 		new_query = factory()
# 		update_from_external_object(new_query, eo)
# 		assert_that(new_query, has_property('term', 'sode no shirayuki'))
# 		assert_that(new_query, has_property('sortOn', 'relevance'))
# 		assert_that(new_query, has_property('searchOn', is_(['note'])))
# 		assert_that(new_query, has_property('creationTime', is_(equal_to(qo.creationTime))))
# 		assert_that(new_query, has_property('context', has_entry('theotokos','Mater Dei')))
