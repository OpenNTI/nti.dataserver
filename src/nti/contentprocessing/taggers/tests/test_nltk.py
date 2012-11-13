import unittest
		
from zope import component

from nti.contentprocessing.taggers import interfaces	

from nti.contentprocessing.tests import ConfiguringTestBase

from hamcrest import assert_that, is_not

class TestNLTK(ConfiguringTestBase):

	def test_backoff_tagger(self):
		tagger = component.getUtility(interfaces.INLTKBackoffNgramTagger)
		assert_that(tagger, is_not(None))

if __name__ == '__main__':
	unittest.main()

