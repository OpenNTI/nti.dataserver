import os
import shutil
import unittest
import tempfile

from nti.contentsearch.spambayes.tokenizer import tokenize
from nti.contentsearch.spambayes.storage import SQL3Classifier

from hamcrest import (assert_that, is_, has_length, equal_to)

class TestStorage(unittest.TestCase):

	ham = """Use the param function in list context"""
	spam = """Youtube delete your video context and can only be accessed on the link posted below"""
		
	def setUp(self):
		super(TestStorage, self).setUp()
		self.path = tempfile.mkdtemp(dir="/tmp")
		self.db_path = os.path.join(self.path, "sample.db")
		
	def tearDown(self):
		super(TestStorage, self).tearDown()
		shutil.rmtree(self.path, True)
		
	def test_trainer( self ):
		sc = SQL3Classifier(self.db_path)
		sc.learn(tokenize(self.ham), False)
		sc.learn(tokenize(self.spam), True)
	
		rc = sc.get_record('context')
		assert_that(rc.spamcount, is_(1))
		assert_that(rc.hamcount, is_(1))
		assert_that(sc.words, has_length(17))
		
		sc2 = SQL3Classifier(self.db_path)
		assert_that(sc2.nham, is_(1))
		assert_that(sc2.nspam, is_(1))
		
	def test_batch( self ):
		sc = SQL3Classifier(self.db_path, True)
		sc.learn(tokenize(self.ham), False)
		c1 = sc.cursor()
		sc.learn(tokenize(self.spam), True)
		c2 = sc.cursor()
		assert_that(c1, equal_to(c2))
		sc.force_commit()
		assert_that(sc.words, has_length(17))

if __name__ == '__main__':
	unittest.main()
