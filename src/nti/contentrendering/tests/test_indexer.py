import os
import shutil
import tempfile
import unittest

from nti.contentrendering.indexer import transform
from nti.contentrendering.indexer import get_or_create_index
from nti.contentrendering.RenderedBook import _EclipseTOCMiniDomTopic
from nti.contentrendering.indexer import _index_book_node as index_book_node
from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook, EmptyMockDocument 
		
from nti.contentrendering.tests import ConfiguringTestBase

from hamcrest import assert_that, has_length

from whoosh.query import (Or, Term)

class TestIndexer(ConfiguringTestBase):

	def setUp(self):
		self.idxdir = tempfile.mkdtemp(dir="/tmp")

	def tearDown(self):
		shutil.rmtree(self.idxdir, True)

	def test_index_book(self):
		indexname='biology'
		path = os.path.join( os.path.dirname( __file__ ),  'intro-biology-rendered-book' )
		book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), path)
		transform(book, indexname=indexname, indexdir=self.idxdir, optimize=False)
		
		idx = get_or_create_index(indexdir=self.idxdir, indexname=indexname, recreate=False)
		q = Term("keywords", u"mathcounts")
		with idx.searcher() as s:
			r = s.search(q, limit=None)
			assert_that(r, has_length(0))

		q = Or([Term("content", u'biology'),])
		with idx.searcher() as s:
			r = s.search(q, limit=None)
			assert_that(r, has_length(26))
			
		q = Or([Term("content", u'homeostasis'),])
		with idx.searcher() as s:
			r = s.search(q, limit=None)
			assert_that(r, has_length(16))
		
		idx.close()

	def _index_file(self, path, indexname, nodename):
		idx = get_or_create_index(indexdir=self.idxdir, indexname=indexname, recreate=True)
		writer = idx.writer(optimize=False, merge=False)		
		node = _EclipseTOCMiniDomTopic(None, path, path, None, nodename)
		index_book_node(writer, node)
		writer.commit(optimize=False, merge=False)
		return idx
			
	def test_index_prealgebra(self):
		indexname='prealgebra'
		path = os.path.join( os.path.dirname( __file__ ),  'why_start_with_arithmetic_.html' )
		idx = self._index_file(path, indexname, 'why start with arithmetic')
		try:
			q = Term("content", u"exotic")
			with idx.searcher() as s:
				r = s.search(q)
				assert_that(r, has_length(1))
		finally:
			idx.close()
		
	def test_index_cohen(self):
		indexname='cohen'
		path = os.path.join( os.path.dirname( __file__ ),  'cohen_vs_california.html' )
		idx = self._index_file(path, indexname, 'cohen vs california')
		try:
			q = Term("content",u"court's")
			with idx.searcher() as s:
				r = s.search(q)
				assert_that(r, has_length(1))
		finally:
			idx.close()
		
if __name__ == '__main__':
	unittest.main()

