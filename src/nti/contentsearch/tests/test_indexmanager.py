import time
import shutil
import unittest
import tempfile
from datetime import datetime

from zope import component

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import QueryObject
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._whoosh_index import create_book_schema
from nti.contentsearch._whoosh_indexstorage import create_directory_index
from nti.contentsearch.indexmanager import create_index_manager_with_repoze
from nti.contentsearch.indexmanager import create_index_manager_with_whoosh
from nti.contentsearch._whoosh_bookindexmanager import WhooshBookIndexManager

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.common import HIT_COUNT

from nti.contentsearch.tests import phrases
from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (is_, has_entry, assert_that)

class _BaseIndexManagerTest(object):

	@classmethod
	def setUpClass(cls):
		cls.now = time.time()
		cls._add_book_data()

	@classmethod
	def _add_book_data(cls):
		cls.now = time.time()
		cls.book_idx_dir = tempfile.mkdtemp(dir="/tmp")
		create_directory_index('bleach', create_book_schema(), cls.book_idx_dir)
		cls.bim = WhooshBookIndexManager('bleach', 'bleach', indexdir=cls.book_idx_dir)

		idx = cls.bim.bookidx
		writer = idx.writer()
		for k, x in enumerate(phrases):
			writer.add_document(ntiid = unicode(make_ntiid(provider=str(k), nttype='bleach', specific='manga')),
								title = unicode(x),
								content = unicode(x),
								quick = unicode(x),
								related= u'',
								section= u'',
								last_modified=datetime.fromtimestamp(cls.now))
		writer.commit()

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.book_idx_dir, True)

	# ----------------

	def is_ngram_search_supported(self):
		features = component.getUtility(search_interfaces.ISearchFeatures)
		return features.is_ngram_search_supported
	
	def is_word_suggest_supported(self):
		features = component.getUtility(search_interfaces.ISearchFeatures)
		return features.is_word_suggest_supported
	
	@WithMockDSTrans
	def test_add_book(self):
		self.im = self.create_index_mananger()
		assert_that(self.im.add_book(indexname='bleach', ntiid='bleach', indexdir=self.book_idx_dir), is_(True))
		assert_that(self.im.add_book(indexname='unknown', ntiid='unknown', indexdir='/tmp'), is_(False))

	@WithMockDSTrans
	def test_search_book(self):
		self.im = self.create_index_mananger()
		self.im.add_book(indexname='bleach', ntiid='bleach', indexdir=self.book_idx_dir)

		hits = self.im.content_search(indexid='bleach', query='omega')
		assert_that(hits, has_entry(HIT_COUNT, 1))

		hits = self.im.content_ngram_search(indexid='bleach', query='ren')
		assert_that(hits, has_entry(HIT_COUNT, 3))

		hits = self.im.content_suggest_and_search(indexid='bleach', query='wen')
		assert_that(hits, has_entry(HIT_COUNT, 1))

		hits = self.im.content_suggest(indexid='bleach', query='extre')
		assert_that(hits, has_entry(HIT_COUNT, 1))

	@WithMockDSTrans
	def test_unified_search(self):
		self._add_notes_and_index(('omega radicals', 'the queen of coffee'))
		self.im.add_book(indexname='bleach', ntiid='bleach', indexdir=self.book_idx_dir)

		q = QueryObject(term='omega', indexid='bleach', username='nt@nti.com')
		hits = self.im.search(q)
		assert_that(hits, has_entry(HIT_COUNT, 2))

		q.term = 'coffee'
		hits = self.im.search(q)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		
	@WithMockDSTrans
	def test_unified_search_ngrams(self):
		
		if not self.is_ngram_search_supported():
			return
		
		self._add_notes_and_index(('omega radicals', 'the queen of coffee'))
		self.im.add_book(indexname='bleach', indexdir=self.book_idx_dir)

		q = QueryObject(term='coff', indexid='bleach', username='nt@nti.com')
		hits = self.im.ngram_search(q)
		assert_that(hits, has_entry(HIT_COUNT, 1))

		q.term = 'omeg'
		hits = self.im.suggest(q)
		assert_that(hits, has_entry(HIT_COUNT, 1))

		hits = self.im.suggest_and_search(q)
		assert_that(hits, has_entry(HIT_COUNT, 2))
		
	@WithMockDSTrans
	def test_unified_search_suggest(self):
		
		if not self.is_word_suggest_supported():
			return
		
		self._add_notes_and_index(('omega radicals', 'the queen of coffee'))
		self.im.add_book(indexname='bleach', indexdir=self.book_idx_dir)

		q = QueryObject(term='omeg', indexid='bleach', username='nt@nti.com')
		hits = self.im.suggest(q)
		assert_that(hits, has_entry(HIT_COUNT, 1))

	@WithMockDSTrans
	def test_unified_search_suggest_and_search(self):
		
		if not self.is_word_suggest_supported():
			return
		
		self._add_notes_and_index(('omega radicals', 'the queen of coffee'))
		self.im.add_book(indexname='bleach', indexdir=self.book_idx_dir)

		q = QueryObject(term='omeg', indexid='bleach', username='nt@nti.com')
		hits = self.im.suggest_and_search(q)
		assert_that(hits, has_entry(HIT_COUNT, 2))
		
	# ----------------

	def _add_notes_to_ds(self, strings=zanpakuto_commands):
		notes = []
		conn = mock_dataserver.current_transaction

		usr = User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )

		for x in strings:
			note = Note()
			note.body = [unicode(x)]
			note.creator = usr.username
			note.containerId = make_ntiid(nttype='bleach', specific='manga')
			conn.add(note)
			notes.append(usr.addContainedObject( note ))
		return notes, usr

	def _add_notes_to_index(self, im, notes):
		for note in notes:
			im.index_user_content(data=note, username='nt@nti.com')
		return notes

	def _add_notes_and_index(self, strings=zanpakuto_commands):
		self.im = self.create_index_mananger()
		notes, usr = self._add_notes_to_ds(strings)
		self._add_notes_to_index(self.im, notes)
		return notes, usr

	@WithMockDSTrans
	def test_add_notes(self):
		self._add_notes_and_index()

	@WithMockDSTrans
	def test_search_notes(self):
		self._add_notes_and_index()

		hits = self.im.user_data_search(query='not_to_be_found', username='nt@nti.com', search_on=('Notes',))
		assert_that(hits, has_entry(HIT_COUNT, 0))

		hits = self.im.user_data_search(query='rage', username='nt@nti.com', search_on=('Notes',))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		
	@WithMockDSTrans
	def test_search_notes_ngrams(self):
		
		if not self.is_ngram_search_supported():
			return
		
		self._add_notes_and_index()
		hits = self.im.user_data_ngram_search(query='deat', username='nt@nti.com', search_on=('note',))
		assert_that(hits, has_entry(HIT_COUNT, 1))

	@WithMockDSTrans
	def test_search_notes_suggest(self):
		
		if not self.is_word_suggest_supported():
			return
		
		self._add_notes_and_index()
		hits = self.im.user_data_suggest(username='nt@nti.com', search_on=('note',), query='flow')
		assert_that(hits, has_entry(HIT_COUNT, 1))

	@WithMockDSTrans
	def test_search_notes_suggest_and_search(self):
		
		if not self.is_word_suggest_supported():
			return
		
		self._add_notes_and_index()
		hits = self.im.user_data_suggest_and_search(query='creat', username='nt@nti.com', search_on=('note',))
		assert_that(hits, has_entry(HIT_COUNT, 1))

	@WithMockDSTrans
	def test_update_delete_note(self):
		notes,_ = self._add_notes_and_index()

		note = notes[0]
		note.body = [u'Shoot To Death']
		self.im.update_user_content(data=note, username='nt@nti.com')
		hits = self.im.user_data_search(query='death', username='nt@nti.com', search_on=('Notes',))
		assert_that(hits, has_entry(HIT_COUNT, 2))

		note = notes[1]
		self.im.delete_user_content(data=note, username='nt@nti.com')
		hits = self.im.user_data_search(query='deviate', username='nt@nti.com', search_on=('Notes',))
		assert_that(hits, has_entry(HIT_COUNT, 0))

class TestIndexManagerWithRepoze(_BaseIndexManagerTest, ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		_BaseIndexManagerTest.setUpClass()

	@classmethod
	def tearDownClass(cls):
		_BaseIndexManagerTest.tearDownClass()

	def setUp(self):
		ConfiguringTestBase.setUp(self)

	def tearDown(self):
		ConfiguringTestBase.tearDown(self)

	def create_index_mananger(self):
		return create_index_manager_with_repoze()

@unittest.skip
class TestIndexManagerWithWhoosh(_BaseIndexManagerTest, ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		_BaseIndexManagerTest.setUpClass()

	@classmethod
	def tearDownClass(cls):
		_BaseIndexManagerTest.tearDownClass()

	def setUp(self):
		ConfiguringTestBase.setUp(self)
		self.whoosh_dir = tempfile.mkdtemp(dir="/tmp")

	def tearDown(self):
		ConfiguringTestBase.tearDown(self)
		shutil.rmtree(self.whoosh_dir, True)

	def create_index_mananger(self):
		return create_index_manager_with_whoosh(indexdir=self.whoosh_dir, use_md5=False)

if __name__ == '__main__':
	unittest.main()
