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
from hamcrest import has_property

import os
import codecs
import unittest

from nti.contentprocessing.langdetection.tika import _TikaLanguageDetector

from nti.contentprocessing.tests import SharedConfiguringTestLayer

class TestTikaLangDetector(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	@property
	def sample_en(self):
		name = os.path.join(os.path.dirname(__file__), 'sample_en.txt')
		with open(name, "r") as f:
			return f.read()

	@property
	def sample_es(self):
		name = os.path.join(os.path.dirname(__file__), 'sample_es.txt')
		with codecs.open(name, "r", "utf-8") as f:
			return f.read()
	@property
	def sample_ru(self):
		name = os.path.join(os.path.dirname(__file__), 'sample_ru.txt')
		with codecs.open(name, "r", "utf-8") as f:
			return f.read()

	def test_lang_detector(self):
		dectector = _TikaLanguageDetector()
		lang = dectector(self.sample_en)
		assert_that(lang, is_not(none()))
		assert_that(lang, has_property('code', is_('en')))

		lang = dectector(self.sample_es)
		assert_that(lang, is_not(none()))
		assert_that(lang, has_property('code', is_('es')))

		lang = dectector(self.sample_ru)
		assert_that(lang, is_not(none()))
		assert_that(lang, has_property('code', is_('ru')))

