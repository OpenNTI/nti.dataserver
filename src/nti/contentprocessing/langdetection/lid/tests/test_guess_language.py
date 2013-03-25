#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from ..guess_language import _LangDetector

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_length)

class TestGuessLanguage(ConfiguringTestBase):

	def test_models(self):
		t = _LangDetector()
		assert_that(t.models, has_length(1))
