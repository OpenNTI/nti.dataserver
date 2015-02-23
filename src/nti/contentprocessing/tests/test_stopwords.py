#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_length
from hamcrest import assert_that

import unittest

from nti.contentprocessing.stopwords import _FileBasedStopWords

from nti.contentprocessing.tests import SharedConfiguringTestLayer

class TestStopWords(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_queryobject_ctor(self):
		util = _FileBasedStopWords()
		assert_that(util.available_languages(), has_length(15))
		words = util.stopwords('en')
		assert_that(words, has_length(570))
		words = util.stopwords('zh')
		assert_that(words, has_length(119))
		words = util.stopwords('ru')
		assert_that(words, has_length(421))
