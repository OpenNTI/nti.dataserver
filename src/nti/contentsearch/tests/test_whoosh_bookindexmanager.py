import time
import shutil
import tempfile
import unittest
from datetime import datetime

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject

from nti.contentsearch import _whoosh_index
from nti.contentsearch._whoosh_index import create_book_schema
from nti.contentsearch._whoosh_indexstorage import create_directory_index
from nti.contentsearch._whoosh_bookindexmanager import WhooshBookIndexManager

from nti.contentsearch.common import (HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS, SNIPPET, NTIID)

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_key, has_entry, has_length, is_not, has_item)

_whoosh_index.compute_ngrams = True

class TestWhooshBookIndexManager(ConfiguringTestBase):
			
	@classmethod
	def setUpClass(cls):
		cls.now = time.time()
		cls.idx_dir = tempfile.mkdtemp(dir="/tmp")
		create_directory_index('bleach', create_book_schema(), cls.idx_dir)
		cls.bim = WhooshBookIndexManager('bleach', indexdir=cls.idx_dir) 
		
		idx = cls.bim.bookidx
		writer = idx.writer()
		for k, x in enumerate(zanpakuto_commands):
			writer.add_document(ntiid = unicode(make_ntiid(provider=str(k), nttype='bleach', specific='manga')),
								title = unicode(x),
								content = unicode(x),
								quick = unicode(x),
								related= u'',
								last_modified=datetime.fromtimestamp(cls.now))
		writer.commit()
			
	@classmethod
	def tearDownClass(cls):
		cls.bim.close()
		shutil.rmtree(cls.idx_dir, True)
		
	def test_search(self):		
		hits = self.bim.search("shield", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'shield'))
		assert_that(hits, has_key(ITEMS))
		
		items = hits[ITEMS]
		assert_that(items, has_length(1))
		
		key = list(items.keys())[0]
		item = items[key]
		assert_that(key, is_(item[NTIID]))
		assert_that(item, has_entry(CLASS, HIT))
		assert_that(item, has_entry(NTIID, is_not(None)))
		assert_that(item, has_entry(CONTAINER_ID,  is_not(None)))
		
		item = toExternalObject(item)
		assert_that(item, has_entry(SNIPPET, 'Rise now and Become my Shield, Lightning, Strike'))
		
	def test_search_start(self):
		hits = self.bim.search("ra*", limit=None)
		assert_that(hits, has_entry(HIT_COUNT, 3))
		assert_that(hits, has_entry(QUERY, 'ra*'))
		assert_that(hits, has_key(ITEMS))
		
	def test_suggest(self):
		hits = self.bim.suggest("ra")
		assert_that(hits, has_entry(HIT_COUNT, 5))
		assert_that(hits, has_entry(QUERY, 'ra'))
		assert_that(hits, has_key(ITEMS))
		
		items = hits[ITEMS]
		assert_that(items, has_length(5))
		assert_that(items, has_item('rage'))
		assert_that(items, has_item('rank'))
		assert_that(items, has_item('rag'))
		assert_that(items, has_item('rai'))
		assert_that(items, has_item('ran'))
		
	def test_ngram_search(self):
		hits = self.bim.ngram_search("sea")
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'sea'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))
		
	def test_suggest_and_search(self):
		hits = self.bim.suggest_and_search("ra")
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, u'rage'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))
		
if __name__ == '__main__':
	unittest.main()
