#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import unittest

from .._alchemy import _AlchemyLanguage
from .._alchemy import _AlchemyTextLanguageDectector

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, none)

class TestAlchemyLangDetector(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestAlchemyLangDetector, cls).setUpClass()
		name = os.path.join(os.path.dirname(__file__), 'sample_en.txt')
		with open(name, "r") as f:
			cls.sample_content_en = f.read()

	@unittest.SkipTest
	def test_alchemy_detector(self):
		lang = _AlchemyTextLanguageDectector()(self.sample_content_en, "NTI-TEST")
		assert_that(lang, is_not(none()))
		assert_that(lang.code, is_('en'))

	def test_alchemy_language(self):
		a = _AlchemyLanguage(ISO_639_1='en', ISO_639_2='a', ISO_639_3='a', name='enlgish')
		assert_that(a.code, is_('en'))
		assert_that(hash(a), is_(12928077669116588L))
		b = _AlchemyLanguage(ISO_639_1='en', ISO_639_2='a', ISO_639_3='a', name='enlgish')
		assert_that(a, is_(b))
		assert_that(str(a), is_('en'))
		assert_that(repr(a), is_('(enlgish,en,a,a)'))


