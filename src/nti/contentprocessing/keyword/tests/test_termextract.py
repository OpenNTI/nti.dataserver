#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import os
import unittest

from nti.contentprocessing.keyword import extract_key_words

from nti.contentprocessing.tests import SharedConfiguringTestLayer

class TestKeyWordExtract(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	# features = ()  # force loading the tagger

	@property
	def sample(self):
		name = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(name, "r") as f:
			return f.read()

	def test_term_extract(self):
		terms = extract_key_words(self.sample)
		terms = [(r.token, r.frequency, r.strength) for r in terms]
		assert_that(sorted(terms),
					is_(sorted([('blood', 4, 1),
								('virus', 3, 1),
								('blood vessel', 1, 2),
								('blood cells', 1, 2),
								('body works', 1, 2),
								('blood cells viruses', 1, 3)])))
