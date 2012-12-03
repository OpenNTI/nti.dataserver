import unittest
		
from nti.contentprocessing.stemmers._lovins import LovinsStemmer

from nti.contentprocessing.tests import ConfiguringTestBase

from hamcrest import assert_that, is_

class TestZopyYXStemmer(ConfiguringTestBase):

	def test_stemmer(self):
		stemmer = LovinsStemmer()
		assert_that(stemmer.stem('viruses'), is_('virus'))
	
if __name__ == '__main__':
	unittest.main()

