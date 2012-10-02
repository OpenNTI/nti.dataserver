import os
import shutil
import tempfile
import unittest

from nti.contentrendering.indexer import transform
from nti.contentrendering.indexer import get_or_create_index
from nti.contentrendering.RenderedBook import _EclipseTOCMiniDomTopic
from nti.contentrendering.indexer import _index_book_node as index_book_node
from nti.contentrendering.tests import NoPhantomRenderedBook, EmptyMockDocument 
		
from hamcrest import assert_that, has_length

from whoosh.query import (Or, Term)

class TestIndexer(unittest.TestCase):

	def setUp(self):
		self.idxdir = tempfile.mkdtemp(dir="/tmp")

	def tearDown(self):
		shutil.rmtree(self.idxdir, True)

	def test_index_book(self):
		indexname='biology'
		path = os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' )
		book = NoPhantomRenderedBook( EmptyMockDocument(), path)
		transform(book, indexname=indexname, indexdir=self.idxdir, optimize=False)
		
		idx = get_or_create_index(indexdir=self.idxdir, indexname=indexname, recreate=False)
		q = Term("keywords", u"mathcounts")
		with idx.searcher() as s:
			r = s.search(q, limit=None)
			assert_that(r, has_length(0))

		q = Or([Term("content", u'biology'),])
		with idx.searcher() as s:
			r = s.search(q, limit=None)
			assert_that(r, has_length(27))
			
		q = Or([Term("content", u'homeostasis'),])
		with idx.searcher() as s:
			r = s.search(q, limit=None)
			assert_that(r, has_length(16))
		
		idx.close()

	def test_index_file(self):
		indexname='prealgebra'
		path = os.path.join( os.path.dirname( __file__ ),  'why_start_with_arithmetic_.html' )

		idx = get_or_create_index(indexdir=self.idxdir, indexname=indexname, recreate=True)
		writer = idx.writer(optimize=False, merge=False)		
		node = _EclipseTOCMiniDomTopic(None, path, path, None, 'why start with arithmetic')
		index_book_node(writer, node)
		writer.commit(optimize=False, merge=False)
		
		q = Term("content", u"exotic")
		with idx.searcher() as s:
			r = s.search(q)
			assert_that(r, has_length(1))
		
		idx.close()
		
if __name__ == '__main__':
	unittest.main()

