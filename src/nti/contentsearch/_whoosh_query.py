from __future__ import print_function, unicode_literals

from whoosh import fields
from whoosh.query import Term
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin
from whoosh.qparser import (GtLtPlugin, PrefixPlugin, WildcardPlugin)

from nti.contentsearch import CaseInsensitiveDict
from nti.contentsearch.common import QueryExpr
from nti.contentsearch.common import (sharedWith_, containerId_, collectionId_, last_modified_)
from nti.contentsearch.common import (last_modified_fields)
		
import logging
logger = logging.getLogger( __name__ )


default_search_plugins =  (GtLtPlugin, DateParserPlugin, PrefixPlugin, WildcardPlugin)

def create_query_parser(fieldname='foo', schema=None, plugins=default_search_plugins):
	qparser = QueryParser(fieldname, schema=schema)
	for pg in plugins or ():
		qparser.add_plugin(pg())
	return qparser

_mappings = CaseInsensitiveDict()
_mappings[sharedWith_] = sharedWith_ 
_mappings[containerId_] = containerId_
_mappings[collectionId_] =	collectionId_
for n in last_modified_fields:
	_mappings[n] = last_modified_
	
def map_to_schema_names(name, stored_names=()):
	name = unicode(name) if name else u''
	if not stored_names: return name
	name = _mappings.get(name.lower(), name)
	return name if name in stored_names else None
	
def get_subqueries(qo, stored_names=(), map_func=map_to_schema_names):
	result = []
	for n, v in qo.get_subqueries():
		n = map_func(n, stored_names)
		if n and v is not None:
			result.append((n,v))
	return result

def parse_subquery(name, value, qparser=None, schema=None, plugins=default_search_plugins):
	result = None
	try:
		text = value
		if isinstance(value, QueryExpr):
			text = value.expr
			qparser = qparser if qparser else create_query_parser(name, schema=schema, plugins=plugins)
			result = qparser.parse(text)
	except:
		result = None
		
	result = result if result else Term(name, text)
	return result
	
def parse_subqueries(qo, stored_names=(), plugins=default_search_plugins, map_func=map_to_schema_names):
	chain = None
	subqueries = get_subqueries(qo, stored_names, map_func)
	for n, v in subqueries:
		op = parse_subquery(n, v, plugins=plugins)
		chain = chain & op if chain else op
	return chain
	
def parse_query(fieldname, qo, schema_or_names, plugins=default_search_plugins, map_func=map_to_schema_names):
	schema = schema_or_names if isinstance(schema_or_names, fields.Schema) else None
	stored_names = schema.stored_names() if schema else schema_or_names
	
	# parse main query
	main_query = parse_subquery(fieldname, QueryExpr(qo.term), schema=schema, plugins=plugins)
	
	# parse subqueries
	subquery_chain = parse_subqueries(qo, stored_names, plugins=plugins, map_func=map_func)
	
	# combine
	parsed_query = main_query & subquery_chain if subquery_chain else main_query
	return parsed_query
