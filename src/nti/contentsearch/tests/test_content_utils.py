#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from nti.contentsearch import content_utils

from nti.contentsearch.tests import SharedConfiguringTestLayer

class TestContentUtils(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_get_content(self):
		t = "Shatter, Kyouka Suigetsu"
		t = content_utils.get_content(t)
		assert_that(t, is_("Shatter Kyouka Suigetsu"))
		
	def test_is_covered_by_ngram_computer(self):
		t = "Shatter, Kyouka Suigetsu"
		t = content_utils.is_covered_by_ngram_computer(t)
		assert_that(t, is_(True))
		
		t = "Su"
		t = content_utils.is_covered_by_ngram_computer(t)
		assert_that(t, is_(True))
		
		t = "u"
		t = content_utils.is_covered_by_ngram_computer(t)
		assert_that(t, is_(False))
		