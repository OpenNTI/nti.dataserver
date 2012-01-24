import os
import shutil
import tempfile
import unittest

from nti.contentsearch.contenttypes import Book
from nti.contentrendering.indexer import get_microdata
from nti.contentrendering.indexer import index_content
from nti.contentrendering.indexer import get_or_create_index

from hamcrest import assert_that, has_length, is_

from whoosh.query import (Or, Term)

class TestIndexer(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		cls.idxdir = tempfile.mkdtemp(dir="/tmp")

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.idxdir, True)

	def _has_tuple(self, results, index, t):
		assert_that(results[index], is_(t))

	def test_get_microdata_string(self):
		raw = """
			<html>
			<a name="one" itemscope itemtype="http://schema.org/CreativeWork">
			<span itemprop="fraction">.</span>
			<span itemprop="multiplication"/>
			<div><h1>to enter</h1></div>
			<img name="two" itemscope itemtype="http://schema.org/CreativeWork" />
			<a name="three" itemscope itemtype="http://schema.org/CreativeWork" >
			<span itemprop="prime">.</span>
			<span itemprop="trinity"/>
			</a>
			</a>
			<a name="four" itemscope itemtype="http://schema.org/CreativeWork" >
			<span itemprop="divisible">.</span>
			<span itemprop="pair"/>
			</a>
			</html>
			"""
		ls = get_microdata(raw)
		assert_that(ls, has_length(4))
		self._has_tuple(ls, 0, (u'one', [u'fraction', u'multiplication']))
		self._has_tuple(ls, 1, (u'four', [u'divisible', u'pair']))
		self._has_tuple(ls, 2, (u'two', []))
		self._has_tuple(ls, 3, (u'three', [u'prime', u'trinity']))

	def test_get_microdata_file(self):

		tf = os.path.join(os.path.dirname(__file__), 'sect0001.html')
		with open(tf, "r") as f:
			raw = f.read()

		ls = get_microdata(raw)
		assert_that(ls, has_length(0))

	def test_index_content(self):
		toc = os.path.join(os.path.dirname(__file__), 'eclipse-toc-complete.xml')
		index_content(toc, indexdir=self.idxdir, optimize=False)
		idx = get_or_create_index(indexdir=self.idxdir, recreate=False)

		q = Term("keywords", u"mathcounts")
		with idx.searcher() as s:
			r = s.search(q)
			assert_that(r, has_length(1))

		q = Or([Term("content", u'rules'), Term("keywords", u"number theory")])
		with idx.searcher() as s:
			r = s.search(q)
			print len(r)
			assert_that(r, has_length(2))

		idx.close()

if __name__ == '__main__':
	unittest.main()

