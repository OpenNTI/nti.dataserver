import os
import shutil
import unittest
import tempfile

from nti.contentsearch.spambayes.tokenizer import tokenize
from nti.contentsearch.spambayes.storage import SQL3Classifier

class TestStorage(unittest.TestCase):

	ham = """Use the param function in list context"""
	spam = """Youtube delete your video context and can only be accessed on the link posted below"""
			
	@classmethod
	def setUpClass(cls):	
		cls.path = tempfile.mkdtemp(dir="/tmp")
		cls.db_path = os.path.join(cls.path, "sample.db")

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.path, True)
	
	def test_trainer( self ):
		sc = SQL3Classifier(self.db_path)
		sc.learn(tokenize(self.ham), False)
		sc.learn(tokenize(self.spam), True)

if __name__ == '__main__':
	unittest.main()
