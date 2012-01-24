import time
import random
import unittest

from datetime import datetime

from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import assert_that

from nti.contentsearch.tests import domain
from nti.contentsearch.tests import phrases
from nti.contentsearch.contenttypes import Book
from nti.contentsearch.indexstorage import DirectoryStorage

import tempfile, shutil

class TestBooks(unittest.TestCase):

	idx = None
	now = time.time()
	idxdir = tempfile.mkdtemp(dir="/tmp")
	prefix = "tag:nextthought.com,2011-07-14:AOPS-HTML-prealgebra-"
	
	@classmethod
	def generate_message(cls, aMin=2, aMax=5):
		return " ".join(random.sample(phrases, random.randint(aMin, aMax)))
	
	@classmethod
	def generate_domain(cls, aMin=1, aMax=3):
		return " ".join(random.sample(domain, random.randint(aMin, aMax)))
	
	@classmethod
	def setUpClass(cls):

		dpath = cls.idxdir
		cls.idx = DirectoryStorage(dpath).get_or_create_index(indexname='prealgebra', schema=Book.schema)
		writer = cls.idx.writer()

		entries = random.randint(30, 50)
		for i in range(0, entries):
			ntiid = cls.prefix + str(i)
			content = unicode(cls.generate_message())
			section = 'section-%s' % i
			as_time = datetime.fromtimestamp(time.time())
			writer.add_document(ntiid=unicode(ntiid),
								title=unicode(cls.generate_domain()),
								content=content,
								quick=content,
								related=u'',
								section=unicode(section),
								last_modified=as_time)

		writer.commit()

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.idxdir, True)

	def test_index_content(self):
		try:
			d = {u"ntiid":u'dummy', u'title':u'dummy', u'content':'dummy',\
				 u'quick':u'dummy', u'related':u'', u'section':u'dummy',\
				 u'order':100, u'last_modified':datetime.fromtimestamp(self.now)}
			Book().index_content(self.idx.writer(), d)
			self.fail()
		except RuntimeError:
			pass

	def test_update_content(self):
		try:
			d = {u"ntiid":u'dummy', u'title':u'dummy', u'content':'dummy',\
				 u'quick':u'dummy', u'related':u'', u'section':u'dummy',\
				 u'order':100, u'last_modified':datetime.fromtimestamp(self.now)}
			Book().update_content(self.idx.writer(), d)
			self.fail()
		except RuntimeError:
			pass
		
	def test_delete_content(self):
		try:
			d = {u"ntiid":u'dummy', u'title':u'dummy', u'content':'dummy',\
				 u'quick':u'dummy', u'related':u'', u'section':u'dummy',\
				 u'order':100, u'last_modified':datetime.fromtimestamp(self.now)}
			Book().delete_content(self.idx.writer(), d)
			self.fail()
		except RuntimeError:
			pass
		
	def _test_search_result(self, result):
		assert_that(result, has_key('Hit Count'))
		assert_that(result, has_key('Items'))
		self.assertEqual(result['Hit Count'], len(result['Items']))

		for _, d in result['Items'].items():
			assert_that(d, has_key('Title'))		
			assert_that(d, has_key('Snippet'))	
			assert_that(d, has_key('ContainerId'))		
			assert_that(d, has_entry('Class', 'Hit'))	
			assert_that(d, has_entry('Type', 'Content'))
			
			
	def test_search(self):
		with self.idx.searcher() as searcher:
			r = Book().search(searcher, "Yellow")
			self._test_search_result(r)
			
	def test_quick_search(self):
		with self.idx.searcher() as searcher:
			r = Book().quick_search(searcher, "brown")
			self._test_search_result(r)
			
	def test_suggest_and_search(self):
		with self.idx.searcher() as searcher:
			r = Book().suggest_and_search(searcher, "alp")
			self._test_search_result(r)
			
			if r['Hit Count'] > 0:
				assert_that(r, has_entry('Query', 'alpha'))
				assert_that(r, has_entry('Suggestions', [u'alpha']))
			
	def test_suggest(self):
		with self.idx.searcher() as searcher:
			r = Book().suggest(searcher, "yell")
			assert_that(r, has_entry('Hit Count', 1))
			assert_that(r, has_entry('Last Modified', 0))
			assert_that(r, has_entry('Items', [u'yellow']))	
			
if __name__ == '__main__':
	unittest.main()
