# -*- coding: utf-8 -*-
"""
Whoosh query utilities

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import math

from zope import component
from zope import interface

from whoosh import scoring
from whoosh.query import Term
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin
from whoosh.qparser import (GtLtPlugin, PrefixPlugin, PhrasePlugin)

from . import interfaces as search_interfaces
from .constants import (content_, quick_, title_, tags_, redactionExplanation_, replacementContent_)

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

	def _get_search_fields(self, qo):
		if qo.is_phrase_search or qo.is_prefix_search:
			result = (content_,)
		else:
			result = (quick_, content_)
		return result

	def _get_whoosh_query(self, fieldname, term, schema):
		try:
			parser = create_query_parser(fieldname, schema=schema)
			return parser.parse(term)
		except:
			return Term(fieldname, term)

	def parse(self, qo, schema):
		parsed_query = None
		query_term = qo.term
		search_fields = self._get_search_fields(qo)
		for fieldname in search_fields:
			query = self._get_whoosh_query(fieldname, query_term, schema)
			parsed_query = query | parsed_query if parsed_query else query
		return parsed_query

_DefaultBookWhooshQueryParser = _DefaultWhooshQueryParser
_DefaultNTICardWhooshQueryParser = _DefaultWhooshQueryParser
_DefaultVideoTranscriptWhooshQueryParser = _DefaultWhooshQueryParser

_DefaultNoteWhooshQueryParser = _DefaultWhooshQueryParser
_DefaultHighlightWhooshQueryParser = _DefaultWhooshQueryParser
_DefaultMessageinfoWhooshQueryParser = _DefaultWhooshQueryParser

class _DefaultRedactionWhooshQueryParser(_DefaultWhooshQueryParser):

	def _get_search_fields(self, qo):
		if qo.is_phrase_search or qo.is_prefix_search:
			result = (content_, redactionExplanation_, replacementContent_)
		else:
			result = (quick_, content_, redactionExplanation_, replacementContent_)
		return result

class _DefaultPostWhooshQueryParser(_DefaultWhooshQueryParser):

	def _get_search_fields(self, qo):
		if qo.is_phrase_search or qo.is_prefix_search:
			result = (content_,)
		else:
			result = (quick_, content_, title_, tags_)
		return result

def parse_query(qo, schema, type_name):
	parser = component.queryUtility(search_interfaces.IWhooshQueryParser, name=type_name)
	if parser is None:
		parser = component.getUtility(search_interfaces.IWhooshQueryParser)
	main_query = parser.parse(qo, schema)
	return main_query
