#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import equal_to
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import os
import gzip
import shutil
import tempfile
import unittest

from nti.contentprocessing.langdetection.tika import builder

from nti.contentprocessing.tests import SharedConfiguringTestLayer

class TestBuilder(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_quick_string_buffer(self):
		qsb = builder.QuickStringBuffer("ichigo")
		assert_that(qsb, is_('ichigo'))
		assert_that(qsb, is_(equal_to(builder.QuickStringBuffer("ichigo"))))
		assert_that(qsb, has_length(6))
		assert_that(str(qsb), is_('ichigo'))

		assert_that(qsb[0:4], is_(['i', 'c', 'h', 'i']))
		assert_that(qsb.subSequence(0, 4), is_('ichi'))

		qsb.append(" Kurosaki")
		assert_that(str(qsb), is_('ichigo Kurosaki'))

		qsb = qsb.lower()
		assert_that(str(qsb), is_('ichigo kurosaki'))

		assert_that(qsb.charAt(-1), is_('i'))

		assert_that(hash(qsb), is_not(none()))

	def test_ngram_entry(self):
		a = builder.NGramEntry("ichigo", 10)
		assert_that(a, has_length(6))
		assert_that(a, has_property('count', 10))
		assert_that(a, has_property('seq', is_('ichigo')))

		b = builder.NGramEntry("zaraki", 3)
		assert_that(a < b, is_(True))

		a.frequency = 10
		b.frequency = 1
		assert_that(a < b, is_(False))

	def test_builder(self):
		lp = builder.LanguageProfilerBuilder()
		source = os.path.join(os.path.dirname(__file__), 'en.ngp')
		assert_that(lp.load(source), is_(14))
		assert_that(lp, has_property('sorted', has_length(14)))
		assert_that(lp.getSimilarity(lp), is_(0))

	def test_create_builder(self):
		source = os.path.join(os.path.dirname(__file__), 'welsh_corpus.txt.gz')
		source = gzip.GzipFile(source)
		profile = builder.LanguageProfilerBuilder.create("test", source)
		try:
			outdir = tempfile.mkdtemp(dir="/tmp")
			target = os.path.join(outdir, "out.ngp")
			profile.save(target)
			assert_that(profile.sorted, has_length(1000))
		finally:
			shutil.rmtree(outdir, True)
			
