import os
import unittest
			
from nti.contentprocessing.concepttagging._alchemy import _AlchemyAPIKConceptTaggger

from nti.contentprocessing.tests import ConfiguringTestBase
		
#from hamcrest import (assert_that, is_, has_length)

class TestConceptTagger(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):		
		name = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(name, "r") as f:
			cls.sample_content = f.read()
			
	#@unittest.SkipTest
	def test_alchemy_cu(self):
		_AlchemyAPIKConceptTaggger()(self.sample_content)
		

if __name__ == '__main__':
	unittest.main()

