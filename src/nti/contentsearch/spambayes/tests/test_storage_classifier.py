import os
import shutil
import unittest
import tempfile
import transaction

from nti.contentsearch.spambayes.tokenizer import tokenize
from nti.contentsearch.spambayes.storage_classifier import SQL3Classifier

from nti.contentsearch.spambayes.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_length)

class TestStorage(ConfiguringTestBase):

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
		transaction.begin()
		sc.learn(tokenize(self.ham), False)
		sc.learn(tokenize(self.spam), True)
		transaction.commit()
		
		rc = sc.get_record('context')
		assert_that(rc.spamcount, is_(1))
		assert_that(rc.hamcount, is_(1))
		assert_that(sc.words, has_length(17))
		
		sc2 = SQL3Classifier(self.db_path)
		assert_that(sc2.nham, is_(1))
		assert_that(sc2.nspam, is_(1))
		assert_that(sc2.words, has_length(17))
		
if __name__ == '__main__':
	unittest.main()
