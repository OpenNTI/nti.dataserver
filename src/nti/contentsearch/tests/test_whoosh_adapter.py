import os
import uuid
import shutil
import tempfile
import unittest

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch import interfaces as search_interfaces

from nti.contentsearch.common import ( 	HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS,
										NTIID, TARGET_OID)

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_key, has_entry, has_length, is_not, has_item)

class TestWhooshUserAdapter(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		cls.db_dir = tempfile.mkdtemp(dir="/tmp")
		os.environ['DATASERVER_DIR']= cls.db_dir
	
	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.db_dir, True)

	def _create_user(self, ds=None, username='nt@nti.com', password='temp001'):
		ds = ds or mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
	
	def _add_notes(self, usr):
		notes = []
		conn = mock_dataserver.current_transaction
		for x in zanpakuto_commands:
			note = Note()
			note.body = [unicode(x)]
			note.creator = usr.username
			note.containerId = make_ntiid(nttype='bleach', specific='manga')
			if conn: conn.add(note)
			note = usr.addContainedObject( note ) 
			notes.append(note)
		return notes

	def _add_user_index_notes(self, do_assert=False):
		username = str(uuid.uuid4()).split('-')[-1] + '@nti.com' 
		usr = self._create_user(username=username )
		notes = self._add_notes(usr)
		uim = search_interfaces.IWhooshEntityIndexManager(usr, None)
		for note in notes:
			result = uim.index_content(note)
			if do_assert:
				assert_that(result, is_(True))
		return notes, usr

	@WithMockDSTrans
	def test_empty(self):
		username = str(uuid.uuid4()).split('-')[-1] + '@nti.com' 
		usr = self._create_user(username=username )
		uim = search_interfaces.IWhooshEntityIndexManager(usr, None)
		assert_that(uim.get_stored_indices(), is_([]))
		assert_that(uim.has_stored_indices(), is_(False))

	@WithMockDSTrans
	def test_index_notes(self):
		_, usr = self._add_user_index_notes(True)
		uim = search_interfaces.IWhooshEntityIndexManager(usr, None)
		assert_that(uim.get_stored_indices(), is_(['note']))
		assert_that(uim.has_stored_indices(), is_(True))

	@WithMockDSTrans
	def test_query_notes(self):
		_, usr = self._add_user_index_notes()
		uim = search_interfaces.IWhooshEntityIndexManager(usr, None)
		
		hits = uim.search("shield", limit=None)
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

		hits = uim.search("*", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))

		hits = uim.search("ra*", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 3))

		hits = uim.search(">ichigo")
		assert_that(hits, has_entry(HIT_COUNT, 0))

	@WithMockDSTrans
	def test_update_note(self):
		notes, usr = self._add_user_index_notes()
		uim = search_interfaces.IWhooshEntityIndexManager(usr, None)
		
		note = notes[5]
		note.body = [u'Blow It Away']
		uim.update_content(note)

		hits = uim.search("shield", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))

		hits = uim.search("blow", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'blow'))

	@WithMockDSTrans
	def test_delete_note(self):
		notes, usr  = self._add_user_index_notes()
		uim = search_interfaces.IWhooshEntityIndexManager(usr, None)
		
		note = notes[5]
		uim.delete_content(note)

		hits = uim.search("shield", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))

	@WithMockDSTrans
	def test_suggest(self):
		_, usr = self._add_user_index_notes()
		uim = search_interfaces.IWhooshEntityIndexManager(usr, None)
		
		hits = uim.suggest("ra")
		assert_that(hits, has_entry(HIT_COUNT, 5))
		assert_that(hits, has_entry(QUERY, 'ra'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		assert_that(items, has_length(5))
		assert_that(items, has_item('ran'))
		assert_that(items, has_item('rag'))
		assert_that(items, has_item('rai'))
		assert_that(items, has_item('rank'))
		assert_that(items, has_item('rage'))

	@WithMockDSTrans
	def test_ngram_search(self):
		_, usr = self._add_user_index_notes()
		uim = search_interfaces.IWhooshEntityIndexManager(usr, None)
		hits = uim.ngram_search("sea")
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'sea'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))

if __name__ == '__main__':
	unittest.main()
