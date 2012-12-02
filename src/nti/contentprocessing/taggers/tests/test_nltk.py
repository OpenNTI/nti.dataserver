import unittest
		
from zope import component

from nti.contentprocessing.taggers import interfaces	

from nti.contentprocessing.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_not, is_)

class TestNLTK(ConfiguringTestBase):

	def test_backoff_tagger_factory(self):
		tagger = component.getUtility(interfaces.INLTKBackoffNgramTaggerFactory)
		assert_that(tagger, is_not(None))
		
	def test_default_tagger(self):
		tagger = component.getUtility(interfaces.ITagger)
		assert_that(tagger, is_not(None))
		assert_that(interfaces.INLTKBackoffNgramTagger.providedBy(tagger), is_(True))

if __name__ == '__main__':
	unittest.main()

