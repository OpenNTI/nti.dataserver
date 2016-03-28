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
from hamcrest import starts_with
from hamcrest import assert_that
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

	def get_source(self):
		return StringIO("<ichigo/>")

	def test_ops(self):
		tmp_dir = tempfile.mkdtemp(dir="/tmp")
		try:
			filer = DirectoryFiler(tmp_dir)
			source = self.get_source()
			href = filer.save("ichigo.xml", source, contentType="text/xml", overwrite=True)
			assert_that(href, is_not(none()))
			assert_that(href, starts_with(tmp_dir))
			
			source = filer.get(href)
			assert_that(source, is_not(none()))
			assert_that(source, verifiably_provides(ISource))
			assert_that(source, has_property('length', is_(9)))
			assert_that(source, has_property('filename', is_("ichigo.xml")))
			assert_that(source, has_property('contentType', is_("text/xml")))

			source = filer.get("/home/foo")
			assert_that(source, is_(none()))
			
			source = self.get_source()
			href = filer.save("ichigo.xml", 
							  source,
							  contentType="text/xml", 
							  overwrite=False)

			assert_that(source, is_not(none()))
			assert_that(href, does_not(ends_with("ichigo.xml")))

			source = self.get_source()
			href = filer.save("ichigo.xml", 
							  source,
							  bucket="bleach",
							  contentType="text/xml", 
							  overwrite=True)
			assert_that(href, ends_with("bleach/ichigo.xml"))
			assert_that(filer.is_bucket("bleach"), is_(True))
			
			href = filer.save("ichigo.xml", 
							  source,
							  bucket="bleach/souls",
							  contentType="text/xml", 
							  overwrite=True)
			assert_that(href, ends_with("bleach/souls/ichigo.xml"))
			
			assert_that(filer.remove(href), is_(True))
			source = filer.get(href)
			assert_that(source, is_(none()))
		finally:
			shutil.rmtree(tmp_dir, True)
