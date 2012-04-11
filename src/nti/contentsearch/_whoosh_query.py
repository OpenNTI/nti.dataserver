from whoosh import fields
from whoosh.query import (And,Term)
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin
from whoosh.qparser import (GtLtPlugin, PrefixPlugin, WildcardPlugin)

from nti.contentsearch.common import (	sharedWith_, containerId_, collectionId_, last_modified_)
from nti.contentsearch.common import (	last_modified_fields)
		
import logging
logger = logging.getLogger( __name__ )

# ----------------------------------

default_search_plugins =  (GtLtPlugin, DateParserPlugin, PrefixPlugin, WildcardPlugin)
_lower_last_modified_fields = [n.lower() for n in last_modified_fields]

# ----------------------------------

def create_query_parser(fieldname='foo', schema=None, plugins=default_search_plugins):
	qparser = QueryParser(fieldname, schema=schema)
	for pg in plugins or ():
		qparser.add_plugin(pg())
	return qparser

def map_to_schema_name(name, stored_names=()):
	"""
	return a field-name that matches the one schema
	""" 
	
	if not stored_names: return name
	
	name = name.lower() if name else u''
	if name in _lower_last_modified_fields:
		name = last_modified_
	elif name == containerId_.lower():
		name = containerId_
	elif name == sharedWith_.lower():
		name = sharedWith_
	elif name == collectionId_.lower():
		name = collectionId_
	return name if name in stored_names else None
	
def get_subqueries(qo, stored_names=(), map_func=map_to_schema_name):
	"""
	return tuples (field-name/value) for the subqueries in the specified query object
	"""
	result = []
	for n, v in qo.get_subqueries():
		n = map_func(n, stored_names)
		if n and v is not None:
			result.append((n,v))
	return result

def parse_or_term(name, value, qparser):
	"""
	parse the specified name value whoosh query spec
	"""
	qparser = qparser or create_query_parser()
	try:
		text = unicode('%s:%s' % (name, value))
		result = qparser.parse(text)
	except:
		result = Term(name, value)
	return result
	
def get_default_parsed_query(fieldname, qo, subqueries=None, stored_names=(), map_func=map_to_schema_name):
	"""
	return an 'And' expression for all the terms in the specified query object
	"""
	qparser = create_query_parser(fieldname)
	subqueries = subqueries or get_subqueries(qo, stored_names, map_func) 
	subqueries = [Term(fieldname, qo.term)] + [parse_or_term(qparser, k, v) for k, v in subqueries]
	parsed_query = And(subqueries)
	return parsed_query
	
def parse_query(fieldname, qo, schema_or_names, plugins=default_search_plugins, map_func=map_to_schema_name):
	text = [qo.term]
	schema = schema_or_names if isinstance(schema_or_names, fields.Schema) else None
	stored_names = schema.stored_names() if schema else schema_or_names
	
	# get any subquery
	subqueries = get_subqueries(qo, stored_names, map_func)
	for n, v in subqueries:
		text.append('AND %s:%s' % (n,v))	
	text = unicode(' '.join(text))
		
	qparser = create_query_parser(fieldname, schema=schema, plugins=plugins)
	try:
		parsed_query = qparser.parse(text)
	except:
		parsed_query = get_default_parsed_query(fieldname, qo, subqueries)
	return parsed_query
