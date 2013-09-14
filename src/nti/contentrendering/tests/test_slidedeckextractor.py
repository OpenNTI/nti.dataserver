#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import shutil
import tempfile

from zope import component

from .. import interfaces
from .. import slidedeckextractor

from . import ConfiguringTestBase
from nti.tests import verifiably_provides


import fudge
from hamcrest import assert_that
from hamcrest import has_length

class TestSlideDeckExtractor(ConfiguringTestBase):

	def setUp(self):
		super(TestSlideDeckExtractor, self).setUp()
		self.temp_dir = tempfile.mkdtemp()

	def tearDown(self):
		shutil.rmtree(self.temp_dir)

	def test_utility(self):
		u = component.queryUtility(interfaces.IRenderedBookExtractor, name="SlideDeckExtractor")
		assert_that(u, verifiably_provides(interfaces.IRenderedBookExtractor) )

	@fudge.patch('nti.contentrendering.RenderedBook.EclipseTOC.save')
	def test_extractor_prmia(self, fake_save):
		fake_save.is_callable()

		source_path = os.path.join(os.path.dirname(__file__), 'prmia_riskcourse')
		extracted = slidedeckextractor.extract(source_path, self.temp_dir)
		assert_that(extracted, has_length(6))
