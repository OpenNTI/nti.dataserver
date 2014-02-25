#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_length
from hamcrest import assert_that

import os
import json
import unittest

from zope import component
from zope.mimetype.interfaces import IContentTypeAware

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.testing.matchers import verifiably_provides

from nti.ntiids.ntiids import make_ntiid

from .. import interfaces as search_interfaces
from ..search_results import empty_search_results
from ..search_results import merge_search_results
from ..search_results import empty_suggest_results
from ..search_results import merge_suggest_results
from ..search_results import empty_suggest_and_search_results

from . import zanpakuto_commands
from . import domain as domain_words
from . import SharedConfiguringTestLayer

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

class TestSearchResults(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	@property
	def messageinfo(self):
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			return json.load(f)

	@classmethod
	def _create_user(cls, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_search_results(self):
		user = self._create_user()
		qo = search_interfaces.ISearchQuery("test")
		sr = component.getUtility(search_interfaces.ISearchResultsCreator)(qo)
		assert_that(sr, is_not(None))
		assert_that(sr, verifiably_provides(search_interfaces.ISearchResults))
		assert_that(sr, verifiably_provides(IContentTypeAware))

		notes = []
		containerid = make_ntiid(nttype='bleach', specific='manga')
		for cmd in zanpakuto_commands:
			note = Note()
			note.body = [unicode(cmd)]
			note.creator = 'nt@nti.com'
			note.containerId = containerid
			note = user.addContainedObject(note)
			notes.append(note)

		sr.extend(notes)
		assert_that(len(sr), is_(len(notes)))

		note = Note()
		note.body = [u'test']
		note.creator = 'nt@nti.com'
		note.containerId = containerid
		note = user.addContainedObject(note)
		sr.add(note)

		count = 0
		for n in sr.hits:
			assert_that(n, is_not(None))
			count = count + 1

		expected = len(notes) + 1
		assert_that(count, is_(expected))

	def test_suggest_results(self):
		qo = search_interfaces.ISearchQuery("test")
		sr = component.getUtility(search_interfaces.ISuggestResultsCreator)(qo)
		assert_that(sr, is_not(None))
		assert_that(sr, verifiably_provides(search_interfaces.ISuggestResults))
		assert_that(sr, verifiably_provides(IContentTypeAware))

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

	@WithMockDSTrans
	def test_suggest_and_search_results(self):
		user = self._create_user()
		qo = search_interfaces.ISearchQuery("test")
		sr = component.getUtility(search_interfaces.ISuggestAndSearchResultsCreator)(qo)
		assert_that(sr, is_not(None))
		assert_that(sr, verifiably_provides(search_interfaces.ISuggestAndSearchResults))
		assert_that(sr, verifiably_provides(IContentTypeAware))

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
			note = user.addContainedObject(note)
			notes.append(note)
		sr.extend(notes)
		assert_that(sr, has_length(len(notes)))

	def test_empty_search_results(self):
		d = empty_search_results(search_interfaces.ISearchQuery("myQuery"))
		assert_that(d, has_length(0))
		assert_that(d.hits, is_([]))

	def test_empty_suggest_result(self):
		d = empty_suggest_results(search_interfaces.ISearchQuery("myQuery"))
		assert_that(d, has_length(0))
		assert_that(d.suggestions, has_length(0))

	def test_empty_suggest_and_search_result(self):
		d = empty_suggest_and_search_results(search_interfaces.ISearchQuery("myQuery"))
		assert_that(d, has_length(0))
		assert_that(d.hits, is_([]))
		assert_that(d.suggestions, has_length(0))

	@WithMockDSTrans
	def test_merge_search_results(self):
		user = self._create_user()
		a = empty_search_results(search_interfaces.ISearchQuery("myQuery"))
		a.prop1 = 'value0'

		b = empty_search_results(search_interfaces.ISearchQuery("myQuery"))
		b.prop1 = 'value1'
		b.prop2 = 'value2'

		containerid = make_ntiid(nttype='bleach', specific='manga')
		for x, cmd in enumerate(zanpakuto_commands):
			note = Note()
			note.body = [unicode(cmd)]
			note.creator = 'nt@nti.com'
			note.containerId = containerid
			note = user.addContainedObject(note)
			result = b if x % 2 == 0 else a
			result.add(note, 1.0)

		assert_that(a.prop1, is_('value0'))

		a = merge_search_results(a, b)
		assert_that(a, has_length(len(zanpakuto_commands)))

		assert_that(a.prop1, is_('value0'))
		assert_that(a.prop2, is_('value2'))

	def test_merge_suggest_results(self):
		a = empty_suggest_results(search_interfaces.ISearchQuery("myQuery"))
		a.prop1 = 'value0'

		b = empty_suggest_results(search_interfaces.ISearchQuery("myQuery"))
		b.prop1 = 'value1'
		b.prop2 = 'value2'

		a.add(['a'])
		b.add(['b', 'c'])
		a = merge_suggest_results(a, b)
		assert_that(a, has_length(3))

		for x in ('a', 'b', 'c'):
			assert_that(a, has_item(x))

		assert_that(a.prop1, is_('value0'))
		assert_that(a.prop2, is_('value2'))
