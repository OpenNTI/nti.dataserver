import uuid
import random
import shutil
import unittest
import tempfile

from zope import component

from whoosh import fields
from whoosh import query
from whoosh.compat import ( u, text_type )

from nti.contentsearch.interfaces import IWhooshIndexStorage
from nti.contentsearch._whoosh_indexstorage import DirectoryStorage
from nti.contentsearch._whoosh_indexstorage import MultiDirectoryStorage

from nti.contentsearch.tests import domain
from nti.contentsearch.tests import ConfiguringTestBase

sample_schema = fields.Schema(id=fields.ID(stored=True, unique=True), content=fields.TEXT(stored=True))

class _IndexStorageTest(object):

	indexdir  = None
	idx_storage = None
	
	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.indexdir, True)
		
	@property
	def storage(self):
		return self.idx_storage
	
	def _add_2_index(self, indexname, entries=None):
		
		index = self.storage.get_or_create_index(indexname=indexname, schema=sample_schema)
		writer = index.writer()
			
		ids = list()
		count = 0
		entries = entries or random.randint(1, 10)
		for _ in xrange(entries):
			content = u(" ").join(random.sample(domain, random.randint(5, 20)))
			oid = str(uuid.uuid1())
			ids.append(oid)
			writer.add_document(id=text_type(oid), content=content)
			count += 1
		
		writer.commit()
		
		return (index, ids)
	
	def test_add_entries(self):
		idx, ids = self._add_2_index("sample1")
		with idx.searcher() as s:
			cnt = len(ids)
			self.assertEqual(cnt, s.doc_count())
			
			q = query.Every()
			results = s.search(q,limit=None)
			self.assertEqual(cnt, len(results))
			
	def test_open_index(self):
		self._add_2_index("sample2")
		try:
			self.idx_storage.open_index(indexname="sample2")
		except:
			self.fail()
			
	def test_optimize_index(self):
		idx, _ = self._add_2_index("sample3")
		try:
			idx.optimize()
		except:
			self.fail()
			
	def test_search_index(self):
		index, _ = self._add_2_index("sample4", 400)
		with index.searcher() as s:
			q = query.Term("content", random.choice(domain))
			results = s.search(q,limit=None)
			self.assertTrue(len(results)>0)
			
	def test_delete_index(self):
		index, ids = self._add_2_index("sample5", 50)
		writer = index.writer()
		writer.delete_by_term('id', unicode(ids[0]))
		writer.commit()
		
		with index.searcher() as s:
			q = query.Term("id", unicode(ids[0]))
			results = s.search(q,limit=None)
			self.assertTrue(len(results) == 0)
			
	def test_component(self):
		storage = component.getUtility(IWhooshIndexStorage)
		self.assertTrue(storage != None)
			
class TestDirectoryStorage(ConfiguringTestBase, _IndexStorageTest):
		
	@classmethod
	def setUpClass(cls):
		cls.indexdir = tempfile.mkdtemp(dir="/tmp")
		cls.idx_storage = DirectoryStorage(cls.indexdir)
		
class TestMultiDirectoryStorage(ConfiguringTestBase, _IndexStorageTest):
		
	@classmethod
	def setUpClass(cls):
		cls.indexdir = tempfile.mkdtemp(dir="/tmp")
		cls.idx_storage = MultiDirectoryStorage(cls.indexdir)
	
if __name__ == '__main__':
	unittest.main()
