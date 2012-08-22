import os
import shutil
import tempfile
import unittest

from nti.contentrendering.indexer import index_content
from nti.contentrendering.indexer import get_or_create_index

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
		toc = os.path.join(os.path.dirname(__file__), 'eclipse-toc-complete.xml')
		index_content(toc, indexdir=self.idxdir, optimize=False, indexname='prealgebra')
		idx = get_or_create_index(indexdir=self.idxdir, recreate=False)

		q = Term("keywords", u"mathcounts")
		with idx.searcher() as s:
			r = s.search(q)
			assert_that(r, has_length(0))

		q = Or([Term("content", u'rules'),])
		with idx.searcher() as s:
			r = s.search(q)
			assert_that(r, has_length(1))

		idx.close()

if __name__ == '__main__':
	unittest.main()

