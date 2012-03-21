import time
import shutil
import tempfile
import unittest
from datetime import datetime

from nti.dataserver.ntiids import make_ntiid

from nti.contentsearch._whoosh_index import create_book_schema
from nti.contentsearch._whoosh_indexstorage import DirectoryStorage
from nti.contentsearch._whoosh_bookindexmanager import WhooshBookIndexManager

from nti.contentsearch.common import ( HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS, SNIPPET, NTIID)

from nti.contentsearch.tests import zanpakuto_commands

from hamcrest import (assert_that, is_, has_key, has_entry, has_length, is_not, has_item)

class TestWhooshBookIndexManager(unittest.TestCase):
			
	@classmethod
	def setUpClass(cls):
		cls.now = time.time()
		cls.idx_dir = tempfile.mkdtemp(dir="/tmp")
		idx = DirectoryStorage(cls.idx_dir).get_or_create_index(indexname='bleach', schema=create_book_schema())
		idx.close()
		
		cls.bim = WhooshBookIndexManager('bleach', indexdir=cls.idx_dir) 
		
		idx = cls.bim.bookidx
		writer = idx.writer()
		for x in zanpakuto_commands:
			writer.add_document(ntiid = unicode(make_ntiid(nttype='bleach', specific='manga')),
								title = unicode(x),
								content = unicode(x),
								quick = unicode(x),
								related= u'',
								section= u'',
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
		assert_that(items[key], has_entry(CLASS, HIT))
		assert_that(items[key], has_entry(NTIID, is_not(None)))
		assert_that(key, is_(items[key][NTIID]))
		assert_that(items[key], has_entry(CONTAINER_ID, 'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(items[key], has_entry(SNIPPET, 'now and Become my SHIELD, Lightning, Strike'))
		
	def test_suggest(self):
		hits = self.bim.suggest("ra")
		assert_that(hits, has_entry(HIT_COUNT, 4))
		assert_that(hits, has_entry(QUERY, 'ra'))
		assert_that(hits, has_key(ITEMS))
		
		items = hits[ITEMS]
		assert_that(items, has_length(4))
		assert_that(items, has_item('rankle'))
		assert_that(items, has_item('raise'))
		assert_that(items, has_item('rain'))
		assert_that(items, has_item('rage'))
		
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
