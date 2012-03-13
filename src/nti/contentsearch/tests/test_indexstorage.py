import os
import uuid
import random
import unittest
import tempfile
import shutil

from ZODB import DB
from ZEO import ClientStorage
from ZODB.blob import BlobStorage
from ZODB.FileStorage import FileStorage

from whoosh import query
from whoosh.compat import u, text_type

from nti.contentsearch.tests import domain
from nti.contentsearch.tests import sample_schema
from nti.contentsearch.indexstorage import ZODBIndexStorage	
	
##########################

class _IndexStorageTest(object):

	@classmethod
	def tearDownClass(cls):
		cls.db.close()
		shutil.rmtree(cls.blob_dir, True)
		
	@property
	def storage(self):
		return self.idx_storage
	
	def dbTrans(self):
		return self.storage.dbTrans()
	
	def _add_2_index(self, indexname, entries=None):
		
		with self.dbTrans():
			index = self.storage.get_or_create_index(indexname=indexname, schema=sample_schema)
			
		with self.dbTrans():
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
		with self.dbTrans(), idx.searcher() as s:
			cnt = len(ids)
			self.assertEqual(cnt, s.doc_count())
			
			q = query.Every()
			results = s.search(q,limit=None)
			self.assertEqual(cnt, len(results))
			
	def test_open_index(self):
		self._add_2_index("sample2")
		with self.dbTrans():
			try:
				self.idx_storage.open_index(indexname="sample2")
			except:
				self.fail()
			
	def test_optimize_index(self):
		idx, _ = self._add_2_index("sample3")
		with self.dbTrans():
			try:
				idx.optimize()
			except:
				self.fail()
			
	def test_search_index(self):
		index, _ = self._add_2_index("sample4", 400)
		with self.dbTrans(), index.searcher() as s:
			q = query.Term("content", random.choice(domain))
			results = s.search(q,limit=None)
			self.assertTrue(len(results)>0)
			
	def test_delete_index(self):
		index, ids = self._add_2_index("sample5", 50)
		with self.dbTrans():
			writer = index.writer()
			writer.delete_by_term('id', unicode(ids[0]))
			writer.commit()
			
			with index.searcher() as s:
				q = query.Term("id", unicode(ids[0]))
				results = s.search(q,limit=None)
				self.assertTrue(len(results) == 0)
			

##########################
		
class TestZODBIndexStorage(_IndexStorageTest, unittest.TestCase):
		
	@classmethod
	def setUpClass(cls):
		cls.blob_dir = tempfile.mkdtemp(dir="/tmp")
		
		storage = FileStorage(os.path.join(cls.blob_dir, 'blobs.fs'))
		blob_storage = BlobStorage(cls.blob_dir, storage)

		cls.db = DB(blob_storage)
		cls.idx_storage = ZODBIndexStorage(db=cls.db)
		
# ------------------------

class TestZODBIndexStorageWithFileLocks(_IndexStorageTest, unittest.TestCase):
		
	@classmethod
	def setUpClass(cls):
		
		cls.blob_dir = tempfile.mkdtemp(dir="/tmp")
		cls.locks_dir= tempfile.mkdtemp(dir="/tmp")
		
		storage = FileStorage(os.path.join(cls.blob_dir, 'blobs.fs'))
		blob_storage = BlobStorage(cls.blob_dir, storage)

		cls.db = DB(blob_storage)
		cls.idx_storage = ZODBIndexStorage(	db=cls.db,\
											use_lock_file=True, 
				 							lock_file_dir=cls.locks_dir)
			
	@classmethod
	def tearDownClass(cls):
		cls.db.close()
		shutil.rmtree(cls.blob_dir, True)
		shutil.rmtree(cls.locks_dir, True)
	
# ------------------------

class TestZEOIndexStorage(_IndexStorageTest, unittest.TestCase):
		
	@classmethod
	def setUpClass(cls):
		
		cls.process= None
		cls.client_dir = tempfile.mkdtemp(dir="/tmp")
		cls.blob_dir = tempfile.mkdtemp(dir=cls.client_dir)
		
		clientPipe = os.path.join(cls.client_dir, "zeosocket" )
		dataFile = os.path.join(cls.client_dir, 'data.fs' )
	
		if not os.path.exists( clientPipe ):
			import ZEO, subprocess, time, sys
		
			tries = 5
			redirect=None 
			while not os.path.exists( clientPipe ) and tries:
				configuration = """
				<zeo>
				address %(clientPipe)s
				</zeo>
				<filestorage 1>
				path %(dataFile)s
				blob-dir %(blobDir)s
				</filestorage>
	
				<eventlog>
				<logfile>
				path %(logfile)s
				format %%(asctime)s %%(message)s
				</logfile>
				</eventlog>
				""" % { 'clientPipe': clientPipe, 'blobDir': cls.blob_dir,
						'dataFile': dataFile, 'logfile': cls.client_dir + '/zeo.log'}
				config_file = cls.client_dir + '/configuration.xml'
				with open( config_file, 'w' ) as f:
					print >> f, configuration
	
				tries = tries - 1
				path = os.path.dirname( ZEO.__file__ ) + "/runzeo.py"
	
				devnull = open('/dev/null', 'w') if redirect else None
				cls.process = \
					subprocess.Popen( [sys.executable, path, "-C", config_file],
								  close_fds=(True if redirect else False),
								  preexec_fn=(os.setsid if redirect else None),
								  stdin=devnull, stdout=devnull, stderr=devnull )
				time.sleep( 5 )
				if devnull is not None: devnull.close()
	
		storage = ClientStorage.ClientStorage( 	clientPipe,\
												blob_dir=cls.blob_dir,\
												shared_blob_dir=True)
	
		cls.db = DB(storage)		
		cls.idx_storage = ZODBIndexStorage(db=cls.db)
		
	@classmethod
	def tearDownClass(cls):
		cls.db.close()
		if cls.process:
			try:
				cls.process.kill()
			except:
				pass
		shutil.rmtree(cls.client_dir, True)
	
if __name__ == '__main__':
	unittest.main()
