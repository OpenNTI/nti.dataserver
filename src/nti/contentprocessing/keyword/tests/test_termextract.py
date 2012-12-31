import os
import unittest
			
from nti.contentprocessing.keyword import extract_key_words
		
from nti.contentprocessing.tests import ConfiguringTestBase
		
from hamcrest import assert_that, is_

class TestTermExtract(ConfiguringTestBase):

	def test_index_content(self):
		name = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(name, "r") as f:
			content = f.read()
			
		terms = extract_key_words(content)
		terms = [(r.norm, r.occur, r.strength) for r in terms]
		assert_that(terms, is_([('blood', 4, 1),
								('virus', 3, 1),
								('blood vessel', 1, 2), 
								('blood cells', 1, 2),
								('body works', 1, 2),
								('blood cells viruses', 1, 3)]))

if __name__ == '__main__':
	unittest.main()

