#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from ..detect_language import _LangDetector

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_)

class TestDetectLanguage(ConfiguringTestBase):

	def test_detect_en(self):
		t = _LangDetector()
		assert_that(t.models, has_length(2))
		result = t(u'accessing protected members and many methods')
		assert_that(result.code, is_('en'))

	def test_detect_de(self):
		t = _LangDetector()
		assert_that(t.models, has_length(2))
		result = t(u'Die Jungfrau mußte sich nicht halten, sie lehnte sich nur leicht gegen den abbröckelnden Marmor des Geländers')
		assert_that(result.code, is_('de'))
