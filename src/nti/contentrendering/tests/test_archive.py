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

from .. import archive
from .. import interfaces
from . import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_in, is_not, none)

class TestArchive(ConfiguringTestBase):

	def setUp(self):
		super(TestArchive, self).setUp()
		self.temp_dir = tempfile.mkdtemp()

	def tearDown(self):
		shutil.rmtree( self.temp_dir )

	def test_utility(self):
		u = component.queryUtility(interfaces.IRenderedBookArchiver)
		assert_that(u, is_not(none()))

	def test_archive_biology(self):
		source_path = os.path.join(os.path.dirname(__file__), 'intro-biology-rendered-book')
		added = archive._archive(source_path, self.temp_dir)
		assert_that(added, has_length(39))
		assert_that('eclipse-toc.xml', is_in(added))
		assert_that('icons/chapters/C2.png', is_in(added))
		assert_that('images/chapters/C2.png', is_in(added))
		assert_that('js/worksheet.js', is_in(added))
		assert_that('styles/prealgebra.css', is_in(added))
