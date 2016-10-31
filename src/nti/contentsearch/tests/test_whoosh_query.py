#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import close_to
from hamcrest import assert_that

import unittest

from whoosh import fields
from whoosh.filedb.filestore import RamStorage

from ..whoosh_query import create_query_parser
from ..whoosh_query import CosineScorerModel as CSM

from . import zanpakuto_commands
from . import SharedConfiguringTestLayer

class TestWhooshQuery(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	schema = fields.Schema(	docid = fields.ID(stored=True, unique=True),
							content = fields.TEXT(stored=True))
			
	def test_cosine_scorer(self):
		idx = RamStorage().create_index(self.schema)
		writer = idx.writer()
		for n, x in enumerate(zanpakuto_commands):
			writer.add_document(docid = unicode(n), content = unicode(x))
		writer.commit()

		with idx.searcher(weighting=CSM) as s:
			qp = create_query_parser(u'content', self.schema)
			hits = s.search(qp.parse(u"shield"), limit=len(zanpakuto_commands))
			whoosh_score = hits[0].score
		
		assert_that(whoosh_score, close_to(2.791, 0.05))
