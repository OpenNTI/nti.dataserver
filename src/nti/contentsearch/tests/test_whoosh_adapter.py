import os
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

	def setUp(self):
		ConfiguringTestBase.setUp(self)
		self.db_dir = tempfile.mkdtemp(dir="/tmp")
		os.putenv('DATASERVER_DIR', self.db_dir)

	def tearDown(self):
		ConfiguringTestBase.tearDown(self)
		shutil.rmtree(self.db_dir, True)

	def _add_notes(self, usr=None, conn=None):
		notes = []
		conn = conn or mock_dataserver.current_transaction
		usr = usr or User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )
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
		ds = ds or mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username='nt@nti.com', password='temp' )
		notes, _  = self._index_notes(usr=usr, do_assert=False)
		return notes, usr

	@WithMockDSTrans
	def xtest_empty(self):
		usr = User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )
		uim = search_interfaces.IWhooshEntityIndexManager(usr, None)
		assert_that(uim.get_stored_indices(), is_([]))
		assert_that(uim.has_stored_indices(), is_(False))

	@WithMockDSTrans
	def xtest_index_notes(self):
		self._index_notes()
		assert_that(self.uim.get_stored_indices(), is_(['note']))
		assert_that(self.uim.has_stored_indices(), is_(True))

	@WithMockDSTrans
	def xtest_query_notes(self):
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

		hits = self.uim.search("*", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, len(zanpakuto_commands)))

		hits = self.uim.search("ra*", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 3))

		hits = self.uim.search(">ichigo")
		assert_that(hits, has_entry(HIT_COUNT, 0))

	@WithMockDSTrans
	def xtest_update_note(self):
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
	def xtest_delete_note(self):
		notes, _  = self._add_user_index_notes()
		note = notes[5]
		self.uim.delete_content(note)

		hits = self.uim.search("shield", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry(QUERY, 'shield'))

	@WithMockDSTrans
	def xtest_suggest(self):
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
	def xtest_ngram_search(self):
		self._add_user_index_notes()
		hits = self.uim.ngram_search("sea")
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'sea'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))

if __name__ == '__main__':
	unittest.main()
