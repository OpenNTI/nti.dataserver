import unittest
		
from zope import component

from nti.contentprocessing.stemmers import interfaces	
from nti.contentprocessing.stemmers._zopyx import ZopyYXStemmer

from nti.contentprocessing.tests import ConfiguringTestBase

from hamcrest import assert_that, is_

class TestZopyYXStemmer(ConfiguringTestBase):

	def test_stemmer(self):
		stemmer = ZopyYXStemmer()
		assert_that(stemmer.stem('viruses'), is_('virus'))
	
	def test_utility(self):
		stemmer = component.getUtility(interfaces.IStemmer, "zopyx")
		assert_that(stemmer.stem('viruses'), is_('virus'))
		assert_that(stemmer.stem('temptation'), is_('temptat'))

if __name__ == '__main__':
	unittest.main()

