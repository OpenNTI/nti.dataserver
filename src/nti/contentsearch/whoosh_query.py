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

from whoosh import scoring
from whoosh.query import Term
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin
from whoosh.qparser import (GtLtPlugin, PrefixPlugin, PhrasePlugin)

from . import constants
from . import interfaces as search_interfaces

default_search_plugins = (GtLtPlugin, DateParserPlugin, PrefixPlugin, PhrasePlugin)

class CosineScorer(scoring.WeightLengthScorer):

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

class CosineScorerModel(scoring.WeightingModel):

	def supports_block_quality(self):
		return True

	def scorer(self, searcher, fieldname, text, qf=1):
		if not searcher.schema[fieldname].scorable:
			return scoring.WeightScorer.for_(searcher, fieldname, text)

		return CosineScorer(searcher, fieldname, text)

def create_query_parser(fieldname, schema=None, plugins=default_search_plugins):
	qparser = QueryParser(fieldname, schema=schema)
	for pg in plugins or ():
		qparser.add_plugin(pg())
	return qparser

@interface.implementer(search_interfaces.IWhooshQueryParser)
class _DefaultWhooshQueryParser(object):

	def get_search_fields(self, qo):
		if qo.is_phrase_search or qo.is_prefix_search:
			result = (constants.content_,)
		else:
			result = (constants.quick_, constants.content_)
		return result

	def get_whoosh_query(self, fieldname, term, schema):
		try:
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
			parsed_query = query | parsed_query if parsed_query else query
		return parsed_query

def parse_query(qo, schema, *args):
	parser = component.getUtility(search_interfaces.IWhooshQueryParser)
	main_query = parser.parse(qo, schema)
	return main_query
