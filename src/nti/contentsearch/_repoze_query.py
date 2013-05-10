# -*- coding: utf-8 -*-
"""
Define repoze query methods.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import inspect

from BTrees.LFBTree import LFBucket

from zope import component
from zope import interface
try:
	from zopyx.txng3.core.parsers.english import QueryParserError
	from zopyx.txng3.core.parsers.english import EnglishQueryParser
except ImportError:  # pypy?
	EnglishQueryParser = None
	QueryParserError = Exception

from repoze.catalog.query import Any as IndexAny
from repoze.catalog.query import Contains as IndexContains
from repoze.catalog.query import DoesNotContain as IndexDoesNotContain

from nti.contentprocessing import split_content
from nti.contentprocessing import interfaces as cp_interfaces

from .common import is_all_query
from . import interfaces as search_interfaces
from .constants import (content_, ngrams_, title_, tags_, redactionExplanation_, replacementContent_)

def _can_use_ngram_field(qo):
	tokens = split_content(qo.term)
	__traceback_info__ = qo.term, tokens
	ncomp = component.getUtility(cp_interfaces.INgramComputer, name=qo.language)
	min_word = min(map(len, tokens)) if tokens else 0
	return min_word >= ncomp.minsize

@interface.implementer(search_interfaces.IRepozeSearchQueryValidator)
class _DefaultSearchQueryValiator(object):

	def validate(self, query):
		text = query.term
		try:
			# auto complete phrase search
			if text.startswith('"') and not text.endswith('"'):
				text += '"'
				query.term = text
			EnglishQueryParser.parse(text)
			return True
		except QueryParserError, e:
			logger.warn("Error while parsing query '%s'. '%s'" % (text, e))
			return False

def validate_query(query, language='en'):
	query = search_interfaces.ISearchQuery(query)
	validator = component.getUtility(search_interfaces.IRepozeSearchQueryValidator, name=language)
	return validator.validate(query)

def allow_keywords(f):
	spec = inspect.getargspec(f)
	return True if spec.keywords else False

def set_default_indexng3(params):
	# make we always rank so we can limit results
	params['ranking'] = True

	# check for limit param
	if 'limit' in params:
		value = params.pop('limit')
		params['ranking_maxhits'] = int(value) if value else sys.maxint

	if 'ranking_maxhits' not in params:
		params['ranking_maxhits'] = sys.maxint

	return params

class Contains(IndexContains):

	def __init__(self, index_name, value, **kwargs):
		IndexContains.__init__(self, index_name, value)
		self.params = dict(kwargs)

	def _apply(self, catalog, names):
		index = self._get_index(catalog)
		if allow_keywords(index.applyContains):
			return index.applyContains(self._get_value(names), **self.params)
		else:
			return index.applyContains(self._get_value(names))

	def negate(self):
		return DoesNotContain(self.index_name, self._value, **self.params)

	@classmethod
	def create_for_indexng3(cls, index_name, value, **kwargs):
		set_default_indexng3(kwargs)
		return Contains(index_name, value, **kwargs)

class DoesNotContain(IndexDoesNotContain):

	def __init__(self, index_name, value, **kwargs):
		IndexDoesNotContain.__init__(self, index_name, value)
		self.params = dict(kwargs)

	def _apply(self, catalog, names):
		index = self._get_index(catalog)
		if allow_keywords(index.applyDoesNotContain):
			return index.applyDoesNotContain(self._get_value(names), **self.params)
		else:
			return index.applyDoesNotContain(self._get_value(names))

	def negate(self):
		return Contains(self.index_name, self._value, **self.params)

	@classmethod
	def create_for_indexng3(cls, index_name, value, **kwargs):
		set_default_indexng3(kwargs)
		return DoesNotContain(index_name, value, **kwargs)

class Any(IndexAny):

	def _apply(self, catalog, names):
		result = super(Any, self)._apply(catalog, names)
		if not hasattr(result, "items"):
			result = LFBucket({x:1.0 for x in result})
		return result

@interface.implementer(search_interfaces.IRepozeQueryParser)
class _DefaultRepozeQueryParser(object):

	def _get_search_fields(self, qo):
		if qo.is_phrase_search or qo.is_prefix_search or not _can_use_ngram_field(qo):
			result = (content_,)
		else:
			result = (ngrams_,)
		return result

	def _get_repoze_query(self, fieldname, term, **kwargs):
		return Contains.create_for_indexng3(fieldname, term, **kwargs)

	def parse(self, qo):
		query_term = qo.term
		search_fields = self._get_search_fields(qo)
		queryobject = None
		for fieldname in search_fields:
			query = self._get_repoze_query(fieldname, query_term)
			if query:
				queryobject = query if queryobject is None else queryobject | query
		return queryobject

_DefaultNoteRepozeQueryParser = _DefaultRepozeQueryParser
_DefaultHighlightRepozeQueryParser = _DefaultRepozeQueryParser
_DefaultMessageinfoRepozeQueryParser = _DefaultRepozeQueryParser

class _DefaultRedactionRepozeQueryParser(_DefaultRepozeQueryParser):

	def _get_search_fields(self, qo):
		if qo.is_phrase_search or qo.is_prefix_search or not _can_use_ngram_field(qo):
			result = (content_, redactionExplanation_, replacementContent_)
		else:
			result = (ngrams_, redactionExplanation_, replacementContent_)
		return result

class _DefaultPostRepozeQueryParser(_DefaultRepozeQueryParser):

	def _get_search_fields(self, qo):
		if qo.is_phrase_search or qo.is_prefix_search or not _can_use_ngram_field(qo):
			result = (content_, title_)
		else:
			result = (ngrams_, title_, tags_)
		return result

	def _get_repoze_query(self, fieldname, term, **kwargs):
		if fieldname == tags_:
			result = Any(fieldname, [term.lower()])
		else:
			result = super(_DefaultPostRepozeQueryParser, self)._get_repoze_query(fieldname, term, **kwargs)
		return result

def parse_query(qo, type_name):
	is_all = is_all_query(qo.term)
	if is_all:
		return is_all, None
	else:
		lang = qo.language
		if not validate_query(qo, lang):
			# the query cannot be parsed by zopyx so change it
			# to avoud an exception during the actual search
			qo.term = u'-'

		parser = component.getUtility(search_interfaces.IRepozeQueryParser, name=type_name)
		queryobject = parser.parse(qo)
		return is_all, queryobject
