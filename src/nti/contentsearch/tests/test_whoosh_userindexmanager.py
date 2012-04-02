import shutil
import tempfile
import unittest

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.ntiids import make_ntiid

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase

from nti.contentsearch._whoosh_userindexmanager import WhooshUserIndexManager
from nti.contentsearch._whoosh_indexstorage import create_directory_index_storage

from nti.contentsearch.common import ( 	HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS, SNIPPET, 
										NTIID, TARGET_OID)

from nti.contentsearch.tests import zanpakuto_commands

from hamcrest import (assert_that, is_, has_key, has_entry, has_length, is_not, has_item)

class TestWhooshUserIndexManager(ConfiguringTestBase):
			
	def setUp(self):
		ConfiguringTestBase.setUp(self)
		self.db_dir = tempfile.mkdtemp(dir="/tmp")
		self.storage = create_directory_index_storage(self.db_dir)
		self.uim = WhooshUserIndexManager('nt@nt.dev', self.storage) 
			
	def tearDown(self):
		ConfiguringTestBase.tearDown(self)
		self.uim.close()
		shutil.rmtree(self.db_dir, True)
		
	def _add_notes(self, usr=None, conn=None):
		notes = []
		conn = conn or mock_dataserver.current_transaction
		usr = usr or User( 'nt@nti.com', 'temp' )
		for x in zanpakuto_commands:
			note = Note()
			note.body = [unicode(x)]
			note.creator = usr.username
			note.containerId = make_ntiid(nttype='bleach', specific='manga')
			if conn: conn.add(note)
			notes.append(usr.addContainedObject( note ))	
		return notes, usr
	
	def _index_notes(self, usr=None, conn=None, do_assert=True):
		notes, usr = self._add_notes(usr=usr, conn=conn)
		for note in notes:		
			result = self.uim.index_content(note)
			if do_assert:
				assert_that(result, is_(True))
		return notes, usr
	
	def _add_user_index_notes(self, ds=None):
		usr = User( 'nt@nti.com', 'temp' )
		ds = ds or mock_dataserver.current_mock_ds
		ds.root['users']['nt@nti.com'] = usr
		notes, _  = self._index_notes(usr=usr, do_assert=False)
		return notes, usr
	
	@WithMockDSTrans
	def test_empty(self):
		assert_that(self.uim.get_stored_indices(), is_([]))
		assert_that(self.uim.has_stored_indices(), is_(False))
		
	@WithMockDSTrans
	def test_index_notes(self):
		self._index_notes()
		assert_that(self.uim.get_stored_indices(), is_(['note']))
		assert_that(self.uim.has_stored_indices(), is_(True))
		
	@WithMockDSTrans
	def test_query_notes(self):
		self._add_user_index_notes()
			
		hits = self.uim.search("shield", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'shield'))
		assert_that(hits, has_key(ITEMS))
		
		items = hits[ITEMS]
		assert_that(items, has_length(1))
		
		key = list(items.keys())[0]
		assert_that(items[key], has_entry(CLASS, HIT))
		assert_that(items[key], has_entry(NTIID, is_not(None)))
		assert_that(items[key], has_entry(TARGET_OID, is_not(None)))
		assert_that(key, is_(items[key][NTIID]))
		assert_that(items[key], has_entry(CONTAINER_ID, 'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(items[key], has_entry(SNIPPET, 'now and Become my SHIELD Lightning Strike'))
		
		hits = self.uim.search("*", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, len(zanpakuto_commands)))
		
		hits = self.uim.search("ra*", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 3))
		
	@WithMockDSTrans
	def test_update_note(self):
		notes, _ = self._add_user_index_notes()
		note = notes[5]
		note.body = [u'Blow It Away']
		self.uim.update_content(note)
		
		hits = self.uim.search("shield", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))
		
		hits = self.uim.search("blow", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'blow'))
		
	@WithMockDSTrans
	def test_delete_note(self):
		notes, _  = self._add_user_index_notes()
		note = notes[5]
		self.uim.delete_content(note)
		
		hits = self.uim.search("shield", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))
		
	@WithMockDSTrans
	def test_suggest(self):
		self._add_user_index_notes()
		hits = self.uim.suggest("ra")
		assert_that(hits, has_entry(HIT_COUNT, 4))
		assert_that(hits, has_entry(QUERY, 'ra'))
		assert_that(hits, has_key(ITEMS))
		
		items = hits[ITEMS]
		assert_that(items, has_length(4))
		assert_that(items, has_item('rankle'))
		assert_that(items, has_item('raise'))
		assert_that(items, has_item('rain'))
		assert_that(items, has_item('rage'))
		
	@WithMockDSTrans
	def test_ngram_search(self):
		self._add_user_index_notes()
		hits = self.uim.ngram_search("sea")
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'sea'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))
		
if __name__ == '__main__':
	unittest.main()
