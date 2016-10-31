#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_length
from hamcrest import assert_that

import os
import shutil
import tempfile
import unittest

from whoosh import index
from whoosh.qparser import QueryParser

from nti.ntiids.ntiids import make_ntiid

from nti.contentindexing.whooshidx.schemas import create_book_schema

from . import find_test
from . import SharedConfiguringTestLayer

class WhooshSchemaTestLayer(SharedConfiguringTestLayer):

	@classmethod
	def _create_index(cls):
		cls.schema = create_book_schema()
		cls.db_dir = tempfile.mkdtemp(dir="/tmp")

		index.create_in(cls.db_dir, cls.schema, "sample")
		cls.index = index.open_dir(cls.db_dir, indexname="sample")

		writer = cls.index.writer()
		path = os.path.join(os.path.dirname(__file__), 'sample.txt')
		with open(path, "r") as f:
			for k, x in enumerate(f.readlines()):
				writer.add_document(ntiid=unicode(make_ntiid(provider=str(k),
												  nttype='bleach', specific='manga')),
									title=unicode(x),
									content=unicode(x),
									quick=unicode(x),)
		writer.commit()

	@classmethod
	def setUp(cls):
		cls._create_index()

	@classmethod
	def testSetUp(cls, test=None):
		cls.test = test or find_test()
		cls.test.schema = cls.schema
		cls.test.db_dir = cls.db_dir
		cls.test.index = cls.index

	@classmethod
	def tearDown(cls):
		cls.index.close()
		shutil.rmtree(cls.db_dir, True)

class TestWhooshSchemas(unittest.TestCase):
			
	layer = WhooshSchemaTestLayer
		
	def test_typeahead(self):
		with self.index.searcher() as s:
			qp = QueryParser("quick", schema=self.schema)
			q = qp.parse(unicode("you"))
			results = s.search(q, limit=None)
			assert_that(results, has_length(2))
			
			q = qp.parse(unicode("you hav"))
			results = s.search(q, limit=None)
			assert_that(results, has_length(1))

			q = qp.parse(unicode("man cas"))
			results = s.search(q, limit=None)
			assert_that(results, has_length(1))
