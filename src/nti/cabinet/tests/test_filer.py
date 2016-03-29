#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import ends_with
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import starts_with
from hamcrest import greater_than
from hamcrest import has_property
does_not = is_not

from nti.testing.matchers import verifiably_provides

import shutil
import tempfile
import unittest

from StringIO import StringIO

from nti.cabinet.filer import DirectoryFiler

from nti.cabinet.interfaces import ISource

from nti.cabinet.tests import SharedConfiguringTestLayer

class TestFiler(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def get_data_source(self):
		return StringIO("<ichigo/>")

	def _test_ops(self, reference=False):
		tmp_dir = tempfile.mkdtemp(dir="/tmp")
		try:
			filer = DirectoryFiler(tmp_dir)
			data = self.get_data_source()
			href = filer.save("ichigo.xml", data, relative=False,
							  contentType="text/xml", overwrite=True,
							  reference=reference)
			assert_that(href, is_not(none()))
			assert_that(href, starts_with(tmp_dir))
			
			source = filer.get(href)
			assert_that(source, is_not(none()))
			assert_that(source, verifiably_provides(ISource))
			assert_that(source, has_property('length', is_(9)))
			assert_that(source, has_property('contentType', is_("text/xml")))
			assert_that(source, has_property('filename', is_("ichigo.xml")))

			assert_that(source.read(), is_("<ichigo/>"))
			assert_that(source, has_property('data', is_("<ichigo/>")))
			source.close()

			with source as ds:
				assert_that(ds.read(), is_("<ichigo/>"))

			source = filer.get("/home/foo")
			assert_that(source, is_(none()))
			
			data = self.get_data_source()
			href = filer.save("ichigo.xml", 
							  data,
							  contentType="text/xml", 
							  overwrite=False,
							  reference=reference)
			assert_that(href, does_not(ends_with("ichigo.xml")))

			data = self.get_data_source()
			href = filer.save("ichigo.xml", 
							  data,
							  bucket="bleach",
							  contentType="text/xml", 
							  overwrite=True,
							  reference=reference)
			assert_that(href, ends_with("bleach/ichigo.xml"))
			assert_that(filer.is_bucket("bleach"), is_(True))
			assert_that(filer.list("bleach"), has_length(greater_than(0)))

			data = self.get_data_source()
			href = filer.save("ichigo.xml", 
							  data,
							  bucket="bleach/souls",
							  contentType="text/xml", 
							  overwrite=True,
							  reference=reference)
			assert_that(href, ends_with("bleach/souls/ichigo.xml"))
			
			assert_that(filer.remove(href), is_(True))
			source = filer.get(href)
			assert_that(source, is_(none()))
		finally:
			shutil.rmtree(tmp_dir, True)
			
	def test_non_reference(self):
		self._test_ops(False)
	
	def test_reference(self):
		self._test_ops(True)
