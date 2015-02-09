#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_key
from hamcrest import has_length
from hamcrest import assert_that

import os
import unittest

from nti.contentprocessing.keyword import alchemy

from nti.contentprocessing.tests import SharedConfiguringTestLayer

@unittest.SkipTest
class TestConceptTagger(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	@property
	def sample(self):
		name = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(name, "r") as f:
			return f.read()

	def test_alchemy_keywords(self):
		terms = alchemy.get_keywords(self.sample, "NTI-TEST")
		terms = {r.token: r.relevance for r in terms}
		assert_that(terms, has_length(20))
		assert_that(terms, has_key(u'knobby green objects'))
		assert_that(terms, has_key(u'blood cells'))
		assert_that(terms, has_key(u'red blood cells'))

