import time
import unittest

from zope import component

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject

from nti.contentsearch._search_query import QueryObject
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._search_highlights import WORD_HIGHLIGHT
from nti.contentsearch.common import (LAST_MODIFIED, HIT_COUNT, ITEMS, QUERY, SUGGESTIONS)
									
import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch.tests import domain as domain_words

from hamcrest import (assert_that, has_entry, greater_than, has_key, has_length, greater_than_or_equal_to)

class TestSearchExternal(ConfiguringTestBase):
			
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
	
	@WithMockDSTrans
	def test_externalize_search_results(self):
		notes = []
		now = time.time()
		qo = QueryObject.create("wind")
		containerId = make_ntiid(nttype='bleach', specific='manga')	
		sr = component.getUtility(search_interfaces.ISearchResultsCreator)(qo)
		sr.highlight_type = WORD_HIGHLIGHT
		usr = self._create_user()
		for cmd in zanpakuto_commands:
			note = Note()
			note.body = [unicode(cmd)]
			note.creator =  usr.username
			note.containerId = containerId
			mock_dataserver.current_transaction.add(note)
			note = usr.addContainedObject( note )
			notes.append(note)
			
		sr.add(notes)
		eo = toExternalObject(sr)
		assert_that(eo, has_entry(QUERY, u'wind'))
		assert_that(eo, has_entry(HIT_COUNT, len(zanpakuto_commands)))
		assert_that(eo, has_key(LAST_MODIFIED))
		assert_that(eo[LAST_MODIFIED], greater_than(now))
		assert_that(eo, has_key(ITEMS))
		assert_that(eo[ITEMS], has_length(len(zanpakuto_commands)))
		
	@WithMockDSTrans
	def test_externalize_suggest_results(self):
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
	def test_externalize_search_suggest_results(self):
		now = time.time()
		qo = QueryObject.create("theotokos")
		sr = component.getUtility(search_interfaces.ISuggestAndSearchResultsCreator)(qo)
		sr.highlight_type = WORD_HIGHLIGHT
		
		suggestions = domain_words[:3]
		sr.add_suggestions(suggestions)
		usr = self._create_user()
		commands = zanpakuto_commands[:5]
		containerId = make_ntiid(nttype='bleach', specific='manga')	
		for cmd in commands:
			note = Note()
			note.body = [unicode(cmd)]
			note.creator =  usr.username
			note.containerId = containerId
			mock_dataserver.current_transaction.add(note)
			note = usr.addContainedObject( note )
			sr.add(note)
			
		eo = toExternalObject(sr)
		assert_that(eo, has_entry(QUERY, u'theotokos'))
		assert_that(eo, has_entry(HIT_COUNT, len(commands)))
		assert_that(eo, has_key(LAST_MODIFIED))
		assert_that(eo[LAST_MODIFIED], greater_than_or_equal_to(now))
		assert_that(eo, has_key(ITEMS))
		assert_that(eo[ITEMS], has_length(len(commands)))
		assert_that(eo[SUGGESTIONS], has_length(len(suggestions)))
		
if __name__ == '__main__':
	unittest.main()
