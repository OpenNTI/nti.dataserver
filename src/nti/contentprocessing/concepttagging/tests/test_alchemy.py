#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import close_to
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

import os
import unittest

from nti.contentprocessing.concepttagging import alchemy

from nti.contentprocessing.tests import SharedConfiguringTestLayer

@unittest.SkipTest
class TestConceptTagger(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	@property
	def sample(self):
		name = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(name, "r") as f:
			return f.read()

	def test_alchemy_ct(self):
		concepts = alchemy.get_ranked_concepts(self.sample, "NTI-TEST")
		assert_that(concepts, has_length(8))
		concept = concepts[0]
		assert_that(concept, is_not(None))
		assert_that(concept.text, is_(u'Federal Bureau of Investigation'))
		assert_that(concept.relevance, is_(close_to(0.97, 0.01)))
		sm = concept.sourcemap
		assert_that(sm, has_length(6))
		assert_that(sm, has_entry('website', u'http://www.fbi.gov',))
		assert_that(sm,
					has_entry(
						u'dbpedia',
						u'http://dbpedia.org/resource/Federal_Bureau_of_Investigation'))
		assert_that(sm, has_entry(u'freebase', u'http://rdf.freebase.com/ns/m.02_1m'))
