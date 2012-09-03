import os
import shutil
import tempfile
import unittest

from nti.contentrendering.indexer import transform
from nti.contentrendering.indexer import get_or_create_index
from nti.contentrendering.tests import NoPhantomRenderedBook, EmptyMockDocument
		
from hamcrest import assert_that, has_length

from whoosh.query import (Or, Term)

class TestIndexer(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		cls.idxdir = tempfile.mkdtemp(dir="/tmp")

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.idxdir, True)

	def test_index_content(self):
		indexname='biology'
		path = os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' )
		book = NoPhantomRenderedBook( EmptyMockDocument(), path)
		transform(book, indexname=indexname, indexdir=self.idxdir)
		
		idx = get_or_create_index(indexdir=self.idxdir, indexname=indexname, recreate=False)
		q = Term("keywords", u"mathcounts")
		with idx.searcher() as s:
			r = s.search(q)
			assert_that(r, has_length(0))

		q = Or([Term("content", u'biology'),])
		with idx.searcher() as s:
			r = s.search(q)
			assert_that(r, has_length(18))

		idx.close()

if __name__ == '__main__':
	unittest.main()

