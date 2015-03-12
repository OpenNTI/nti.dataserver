#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh query

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import math

from zope import component
from zope import interface

from whoosh.query import Term
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin
from whoosh.qparser import GtLtPlugin, PrefixPlugin, PhrasePlugin

from whoosh.scoring import WeightScorer
from whoosh.scoring import WeightingModel
from whoosh.scoring import WeightLengthScorer

from nti.contentindexing.whooshidx import TITLE
from nti.contentindexing.whooshidx import QUICK
from nti.contentindexing.whooshidx import CONTENT

from .interfaces import IWhooshQueryParser

default_search_plugins = (GtLtPlugin, DateParserPlugin, PrefixPlugin, PhrasePlugin)

class CosineScorer(WeightLengthScorer):

	def __init__(self, searcher, fieldname, text, qtf=1.0, qmf=1.0):
		# IDF and average field length are global statistics, so get them from
		# the top-level searcher
		parent = searcher.get_parent()  # returns self if no parent
		self.idf = parent.idf(fieldname, text)
		self.qtf = qtf
		self.qmf = qmf
		self.setup(searcher, fieldname, text)

	def _score(self, weight, length):
		DTW = (1.0 + math.log(weight)) * self.idf
		QTW = ((0.5 + (0.5 * self.qtf / self.qmf))) * self.idf
		rank = math.sqrt(DTW * QTW)
		return rank

class CosineScorerModel(WeightingModel):

	def supports_block_quality(self):
		return True

	def scorer(self, searcher, fieldname, text, qf=1):
		if not searcher.schema[fieldname].scorable:
			return WeightScorer.for_(searcher, fieldname, text)
		return CosineScorer(searcher, fieldname, text)

def create_query_parser(fieldname, schema=None, plugins=default_search_plugins):
	qparser = QueryParser(fieldname, schema=schema)
	for pg in plugins or ():
		qparser.add_plugin(pg())
	return qparser

@interface.implementer(IWhooshQueryParser)
class _DefaultWhooshQueryParser(object):

	def get_search_fields(self, qo):
		if qo.is_phrase_search or qo.is_prefix_search:
			result = (CONTENT, TITLE)
		else:
			result = (QUICK, CONTENT, TITLE)
		return result

	def get_whoosh_query(self, fieldname, term, schema):
		try:
			if schema is not None and fieldname not in schema:
				return None
			else:
				parser = create_query_parser(fieldname, schema=schema)
				return parser.parse(term)
		except Exception:
			return Term(fieldname, term)

	def parse(self, qo, schema):
		parsed_query = None
		query_term = qo.term
		search_fields = self.get_search_fields(qo)
		for fieldname in search_fields:
			query = self.get_whoosh_query(fieldname, query_term, schema)
			if query is not None:
				parsed_query = query | parsed_query if parsed_query else query
		if parsed_query is None:
			__traceback_info__ = qo, schema
			raise AssertionError("Could not parse query")
		return parsed_query

def parse_query(qo, schema, *args):
	parser = component.getUtility(IWhooshQueryParser)
	main_query = parser.parse(qo, schema)
	return main_query
