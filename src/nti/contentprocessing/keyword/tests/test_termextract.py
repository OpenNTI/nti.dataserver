import os
import unittest
			
from nti.contentprocessing.keyword import extract_key_words
from nti.contentprocessing.keyword._alchemy import _AlchemyAPIKeyWorExtractor

from nti.contentprocessing.tests import ConfiguringTestBase
		
from hamcrest import (assert_that, is_, has_length)

class TestKeyWordExtract(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):		
		name = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(name, "r") as f:
			cls.sample_content = f.read()
			
	def test_term_extract(self):
		terms = extract_key_words(self.sample_content)
		terms = [(r.token, r.frequency, r.strength) for r in terms]
		assert_that(terms, is_([('blood', 4, 1),
								('virus', 3, 1),
								('blood vessel', 1, 2), 
								('blood cells', 1, 2),
								('body works', 1, 2),
								('blood cells viruses', 1, 3)]))
		
	@unittest.SkipTest
	def test_alchemy_extract(self):
		terms = _AlchemyAPIKeyWorExtractor()(self.sample_content)
		terms = [(r.token, r.relevance) for r in terms]
		assert_that(terms, has_length(15))
		assert_that(terms[0], is_((u'blood cells', 0.998273)))
		assert_that(terms[1], is_((u'knobby green objects', 0.80723)))
		assert_that(terms[2], is_((u'viruses', 0.7604)))
		assert_that(terms[3], is_((u'red blood cells', 0.732536)))

if __name__ == '__main__':
	unittest.main()

