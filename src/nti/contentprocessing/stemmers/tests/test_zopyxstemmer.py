import unittest
			
from nti.contentprocessing.stemmers import ZopyYXStemmer
		
from hamcrest import assert_that, is_

class TestZopyYXStemmer(unittest.TestCase):

	def test_stemmer(self):
		stemmer = ZopyYXStemmer()
		assert_that(stemmer.stem('viruses'), is_('virus'))

if __name__ == '__main__':
	unittest.main()

