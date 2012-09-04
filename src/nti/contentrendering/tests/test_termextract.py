import os
import unittest

try:
	#need to download or install the corpus.
	from nltk.corpus import brown
	skip = False
except:
	skip = True
			
from nti.contentrendering.termextract import extract_key_words
		
from hamcrest import assert_that, is_

@unittest.skipIf(skip, "nltk corpus not installed")
class TestIndexer(unittest.TestCase):

	def test_index_content(self):
		name = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(name, "r") as f:
			content = f.read()
			
		terms = extract_key_words(content)
		assert_that(terms, is_([('blood vessel', 1, 2), 
								('blood cells', 1, 2),
								('virus', 3, 1),
								('blood', 4, 1),
								('body works', 1, 2),
								('blood cells viruses', 1, 3)]))	

if __name__ == '__main__':
	unittest.main()

