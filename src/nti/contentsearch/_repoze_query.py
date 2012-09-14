from __future__ import print_function, unicode_literals

import sys
import inspect

from zopyx.txng3.core.parsers.english import EnglishQueryParser

from repoze.catalog.query import Eq
from repoze.catalog.query import Query
from repoze.catalog.query import Contains as IndexContains
from repoze.catalog.query import parse_query as rz_parse_query
from repoze.catalog.query import DoesNotContain as IndexDoesNotContain

from nti.contentsearch.common import QueryExpr
from nti.contentsearch.common import is_all_query
from nti.contentsearch.common import (sharedWith_, containerId_, collectionId_, id_, oid_, ntiid_,
									  ID, LAST_MODIFIED, CONTAINER_ID, COLLECTION_ID, OID, NTIID, CREATOR)
from nti.contentsearch.common import (last_modified_fields)
from nti.contentsearch._datastructures import CaseInsensitiveDict

import logging
logger = logging.getLogger( __name__ )

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

_mappings = CaseInsensitiveDict()
_mappings[sharedWith_] = sharedWith_
_mappings[containerId_] = CONTAINER_ID
_mappings[collectionId_] = COLLECTION_ID
_mappings[CREATOR] = CREATOR
_mappings[id_] = ID
_mappings[oid_] = OID
_mappings[ntiid_] = NTIID
for n in last_modified_fields:
	_mappings[n] = LAST_MODIFIED
	
def map_to_key_names(name, stored_names=()):
	name = unicode(name) if name else u''
	if not stored_names: return name
	name = _mappings.get(name, name)
	return name if name in stored_names else None

def get_subqueries(qo, stored_names=(), map_func=map_to_key_names):
	result = []
	for n, v in qo.get_subqueries():
		n = map_func(n, stored_names)
		if n and v is not None: 
			result.append((n,v))
	return result

def parse_subquery(fieldname, value):
	result = None
	try:
		text = value
		if isinstance(value, QueryExpr):
			text = value.expr
			result = rz_parse_query(text)
			if not isinstance(result, Query):
				result = None 
	except:
		result = None
	
	result = result if result else Eq(fieldname, text)
	return result
	
def parse_subqueries(qo, stored_names=(), map_func=map_to_key_names):
	chain = None
	subqueries = get_subqueries(qo, stored_names, map_func)
	for n, v in subqueries:
		op = parse_subquery(n, v)
		chain = chain & op if chain else op
	return chain
	
def check_query(query):
	try:
		EnglishQueryParser.parse(query)
		return True
	except Exception, e:
		logger.warn("Error while parsing query '%s'. '%s'" % (query, e))
		return False
	
def parse_query(catalog, fieldname, qo):
	is_all = is_all_query(qo.term)
	subquery_chain = parse_subqueries(qo, catalog.keys())
	if is_all:
		return is_all, subquery_chain
	else:
		query_term = qo.term
		if not check_query(query_term): 
			query_term = u'-'
			subquery_chain = None
		queryobject = Contains.create_for_indexng3(fieldname, query_term, limit=qo.limit)
		queryobject = queryobject & subquery_chain if subquery_chain else queryobject
		return is_all, queryobject
