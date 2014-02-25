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

from nti.contentsearch.whoosh_schemas import create_book_schema

from . import find_test
from . import SharedConfiguringTestLayer

class WhooshSchemaTestLayer(SharedConfiguringTestLayer):

	@classmethod
	def testSetUp(cls, test=None):
		super(WhooshSchemaTestLayer, cls).testSetUp(test)
		cls.test = test = test or find_test()
		test.db_dir = tempfile.mkdtemp(dir="/tmp")

		test.schema = create_book_schema()
		index.create_in(test.db_dir, test.schema, "sample")
		test.index = index.open_dir(test.db_dir, indexname="sample")

		writer = test.index.writer()
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
	def tearDown(cls):
		super(WhooshSchemaTestLayer, cls).tearDown()
		cls.test.index.close()
		shutil.rmtree(cls.test.db_dir, True)

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
