#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import unittest

from .. import extract_key_words
from .._alchemy import _AlchemyAPIKeyWorExtractor

from ...tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_length)

class TestKeyWordExtract(ConfiguringTestBase):

	features = ()  # force loading the tagger

	@classmethod
	def setUpClass(cls):
		super(TestKeyWordExtract, cls).setUpClass()
		name = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(name, "r") as f:
			cls.sample_content = f.read()

	def test_term_extract(self):
		terms = extract_key_words(self.sample_content)
		terms = [(r.token, r.frequency, r.strength) for r in terms]
		assert_that(sorted(terms),
					is_(sorted([('blood', 4, 1),
								('virus', 3, 1),
								('blood vessel', 1, 2),
								('blood cells', 1, 2),
								('body works', 1, 2),
								('blood cells viruses', 1, 3)])))

	@unittest.SkipTest
	def test_alchemy_extract(self):
		terms = _AlchemyAPIKeyWorExtractor()(self.sample_content, "NTI-TEST")
		terms = [(r.token, r.relevance) for r in terms]
		assert_that(terms, has_length(15))
		assert_that(terms[0], is_((u'blood cells', 0.998273)))
		assert_that(terms[1], is_((u'knobby green objects', 0.80723)))
		assert_that(terms[2], is_((u'viruses', 0.7604)))
		assert_that(terms[3], is_((u'red blood cells', 0.732536)))
