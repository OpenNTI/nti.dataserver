import time
import unittest

from datetime import datetime

from nti.contentsearch.indexmanager import IndexManager
from nti.contentsearch.tests import phrases
from nti.contentsearch.contenttypes import Book
from nti.contentsearch.indexstorage import DirectoryStorage

import tempfile, shutil

class TestIndexManager(unittest.TestCase):

	now = time.time()
	idxdir = tempfile.mkdtemp(dir="/tmp")

	@classmethod
	def setUpClass(cls):

		dpath = cls.idxdir
		idx = DirectoryStorage(dpath).get_or_create_index(indexname='prealgebra', schema=Book.schema)
		writer = idx.writer()

		as_time = datetime.fromtimestamp(cls.now)
		writer.add_document(ntiid=u'aop-10',
							title=u'nothing',
							content=u'alpha',
							quick=u'',
							related=u'',
							section=u'',
							last_modified=as_time)

		writer.commit()
		idx.close()

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.idxdir, True)

	def __init__(self, *args, **kargs):
		super(TestIndexManager, self).__init__(*args, **kargs)
		self.user_index_dir = None

	def setUp(self):
		self.user_index_dir = tempfile.mkdtemp(dir="/tmp")

	def tearDown(self):
		shutil.rmtree(self.user_index_dir, True)

	def get_notes(self):
		result = list()
		for x in xrange(10):
			d = {}
			d['CollectionID'] = 'prealgebra'
			d['OID'] = '0x' + str(x).encode('hex')
			d['ContainerId'] = "aops-" + str(x)
			d['Creator'] = 'ntdev@nextthought.com'
			d["Last Modified"] = self.now
			d['body'] = phrases[x]
			d['sharedWith'] = ['cutz@nextthought.com', 'cs@nt.com']
			d['references'] = ['aops-main']
			d['id'] = x
			result.append(d)
		return result

	def create_im(self, add_book=True):
		im = IndexManager(user_index_dir=self.user_index_dir)
		if add_book:
			im.add_book(self.idxdir)
		return im

	def test_add_book(self):
		im = self.create_im(False)
		self.assertTrue(im.add_book(self.idxdir))
		self.assertFalse(im.add_book("/tmp/","dir_unexisting"))
		im.close()

	def add_notes(self, im):
		for d in self.get_notes():
			im.index_user_content(d, username='ntdev@nextthought.com', typeName='Notes')

	def test_add_notes(self):
		im = self.create_im()
		self.add_notes(im)
		im.close()

	def test_search_empty_notes(self):
		im = self.create_im()
		results = im.user_data_search("not_to_be_found", username='ntdev@nextthought.com', search_on=('Notes',))
		self.assertEqual(results['Hit Count'], 0)
		im.close()

	def test_search_notes(self):
		im = self.create_im()
		self.add_notes(im)

		results = im.user_data_search("alpha", username='ntdev@nextthought.com', search_on=('Notes',))
		self.assertEqual(results['Hit Count'], 1)
		items = results['Items']
		self.assertTrue(items[u'0x32']['ContainerId'])
		self.assertEqual(items[u'0x32'][u'Creator'],u'ntdev@nextthought.com')	
		
		results = im.content_search("alpha", indexname='prealgebra')
		self.assertEqual(results['Hit Count'], 1)

		im.close()
		
	def test_quick_search_notes(self):
		im = self.create_im()
		self.add_notes(im)

		results = im.user_data_quick_search("gree", username='ntdev@nextthought.com', search_on=('Notes',))
		self.assertEqual(results['Hit Count'], 1)
		items = results['Items']
		self.assertTrue(items[u'0x31']['ContainerId'])
		self.assertEqual(items[u'0x31'][u'Snippet'],u'')	
		self.assertEqual(items[u'0x31'][u'Creator'],u'ntdev@nextthought.com')	
		im.close()
		
	def test_user_data_suggest(self):
		im = self.create_im()
		self.add_notes(im)

		results = im.user_data_suggest("gree", username='ntdev@nextthought.com', search_on=('Notes',))
		self.assertEqual(results['Hit Count'], 1)
		items = results['Items']
		self.assertEqual(items[0], u'green')
		
		im.close()
		
	def test_user_data_suggest_and_search(self):
		im = self.create_im()
		self.add_notes(im)

		results = im.user_data_suggest_and_search("render", username='ntdev@nextthought.com', search_on=('Notes',))
		self.assertEqual(results['Hit Count'], 1)
		self.assertEqual(results['Suggestions'],  [u'rendering', u'rendered'])
		items = results['Items']
		self.assertEqual(items[u'0x35'][u'Snippet'],u'Three RENDERED four five')		
		im.close()
		
if __name__ == '__main__':
	unittest.main()
