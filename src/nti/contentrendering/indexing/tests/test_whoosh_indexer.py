import os
import shutil
import tempfile
import unittest

from whoosh.query import (Or, Term)

from nti.contentrendering.RenderedBook import _EclipseTOCMiniDomTopic
from nti.contentrendering.indexing._whoosh_indexer import _DefaultWhooshIndexer
from nti.contentrendering.indexing._whoosh_indexer import _BookFileWhooshIndexer
from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook, EmptyMockDocument 

from nti.contentrendering.tests import ConfiguringTestBase

from hamcrest import assert_that, has_length

class TestWhooshIndexer(ConfiguringTestBase):

	def setUp(self):
		ConfiguringTestBase.setUp(self)
		self.idxdir = tempfile.mkdtemp(dir="/tmp")

	def tearDown(self):
		ConfiguringTestBase.tearDown(self)
		shutil.rmtree(self.idxdir, True)

	def _index_book(self, indexer):
		indexname='biology'
		path = os.path.join( os.path.dirname( __file__ ),  '../../tests/intro-biology-rendered-book' )
		book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), path)
		
		idx = indexer.create_index(self.idxdir, indexname)
		writer = idx.writer(optimize=False, merge=False)	
		indexer.process_book(book, writer)
		writer.commit(optimize=False, merge=False)
		
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
		
	def test_default_index__book(self):
		self._index_book(_DefaultWhooshIndexer())
		
	def _index_file(self, path, indexname, nodename, indexer=None):
		indexer = indexer or _DefaultWhooshIndexer()
		idx = indexer.create_index(self.idxdir, indexname)
		writer = idx.writer(optimize=False, merge=False)		
		node = _EclipseTOCMiniDomTopic(None, path, path, None, nodename)
		indexer.process_topic(node, writer)
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
		indexer = _BookFileWhooshIndexer()
		path = os.path.join( os.path.dirname( __file__ ),  'cohen_vs_california.html' )
		idx = self._index_file(path, indexname, 'cohen vs california', indexer)
		try:
			q = Term("content",u"court's")
			with idx.searcher() as s:
				r = s.search(q)
				assert_that(r, has_length(1))
		finally:
			idx.close()
		
if __name__ == '__main__':
	unittest.main()

