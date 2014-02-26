#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

import os
import unittest

from ..alchemy import _AlchemyLanguage
from ..alchemy import _AlchemyTextLanguageDectector

from nti.contentprocessing.tests import SharedConfiguringTestLayer

class TestAlchemyLangDetector(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	@property
	def sample_en(self):
		name = os.path.join(os.path.dirname(__file__), 'sample_en.txt')
		with open(name, "r") as f:
			return f.read()

	@unittest.SkipTest
	def test_alchemy_detector(self):
		lang = _AlchemyTextLanguageDectector()(self.sample_en, "NTI-TEST")
		assert_that(lang, is_not(none()))
		assert_that(lang.code, is_('en'))

	def test_alchemy_language(self):
		a = _AlchemyLanguage(ISO_639_1='en', ISO_639_2='a', ISO_639_3='a', name='enlgish')
		assert_that(a.code, is_('en'))
		b = _AlchemyLanguage(ISO_639_1='en', ISO_639_2='a', ISO_639_3='a', name='enlgish')
		assert_that(a, is_(b))
		assert_that(hash(a), is_(hash(b) ) )
		assert_that(str(a), is_('en'))
		assert_that(repr(a), is_('(enlgish,en,a,a)'))
