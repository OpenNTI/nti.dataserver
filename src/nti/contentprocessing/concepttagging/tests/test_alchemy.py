import os
import unittest
			
from nti.contentprocessing.concepttagging._alchemy import _AlchemyAPIKConceptTaggger

from nti.contentprocessing.tests import ConfiguringTestBase
		
from hamcrest import (assert_that, is_, is_not, has_length, close_to, has_entry)

class TestConceptTagger(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):		
		name = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(name, "r") as f:
			cls.sample_content = f.read()
			
	@unittest.SkipTest
	def test_alchemy_ct(self):
		concepts = _AlchemyAPIKConceptTaggger()(self.sample_content)
		assert_that(concepts, has_length(8))
		concept = concepts[0]
		assert_that(concept, is_not(None))
		assert_that(concept.text, is_(u'Federal Bureau of Investigation'))
		assert_that(concept.relevance, is_(close_to(0.97, 0.01)))	
		sm = concept.sourcemap
		assert_that(sm, has_length(6))
		assert_that(sm, has_entry('website', u'http://www.fbi.gov',))
		assert_that(sm, has_entry(u'dbpedia', u'http://dbpedia.org/resource/Federal_Bureau_of_Investigation'))
		assert_that(sm, has_entry(u'freebase', u'http://rdf.freebase.com/ns/guid.9202a8c04000641f8000000000017c33'))
		
if __name__ == '__main__':
	unittest.main()

