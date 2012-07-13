import os
import shutil
import unittest
import tempfile

from nti.contentsearch.spambayes.tokenizer import tokenize
from nti.contentsearch.spambayes.utils import create_sql3classifier_db

from hamcrest import (assert_that, is_, greater_than_or_equal_to, has_length)

class TestUtis(unittest.TestCase):
	
	def setUp(self):
		super(TestUtis, self).setUp()
		self.path = tempfile.mkdtemp(dir="/tmp")
		self.dbpath = os.path.join(self.path, "sample.db")
		
	def tearDown(self):
		super(TestUtis, self).tearDown()
		shutil.rmtree(self.path, True)
		
	def test_create_sql3classifier_db( self ):
		directory = os.path.dirname(__file__)
		sc = create_sql3classifier_db(self.dbpath, directory, fnfilter='_spam*')
		assert_that(sc.words, has_length(1028))
		rc = sc.get_record('and')
		assert_that(rc.spamcount, is_(3))
		
		text = 'You Will Sell A Product Which Costs Nothing'
		prob = sc.spamprob(tokenize(text), False)
		assert_that(prob, greater_than_or_equal_to(0.99))

if __name__ == '__main__':
	unittest.main()
