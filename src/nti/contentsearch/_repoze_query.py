# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys
import inspect

from zope import component
from zope import interface
from zopyx.txng3.core.parsers.english import EnglishQueryParser

from repoze.catalog.query import Contains as IndexContains
from repoze.catalog.query import DoesNotContain as IndexDoesNotContain

from .common import is_all_query
from . import interfaces as search_interfaces

logger = __import__('logging').getLogger(__name__)

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

@interface.implementer( search_interfaces.IRepozeSearchQueryValidator )
class _DefaultSearchQueryValiator(object):
	
	def validate(self, query):
		query = query.term if search_interfaces.ISearchQuery.providedBy(query) else query
		try:
			EnglishQueryParser.parse(query)
			return True
		except Exception, e:
			logger.warn("Error while parsing query '%s'. '%s'" % (query, e))
			return False
	
def validate_query(query, language='en'):
	validator = component.getUtility(search_interfaces.IRepozeSearchQueryValidator, name=language)
	return validator.validate(query)
	
def parse_query(catalog, search_fields, qo):
	is_all = is_all_query(qo.term)
	if is_all:
		return is_all, None
	else:
		query_term = qo.term
		if not validate_query(query_term): 
			query_term = u'-'
		
		queryobject = None
		for fieldname in search_fields:
			#TODO: contains operation depends on the field type
			contains = Contains.create_for_indexng3(fieldname, query_term, limit=qo.limit)
			queryobject = contains if queryobject is None else queryobject | contains
			
		return is_all, queryobject
