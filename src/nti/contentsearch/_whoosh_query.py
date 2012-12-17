from __future__ import print_function, unicode_literals

from whoosh import fields
from whoosh.query import Term
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin
from whoosh.qparser import (GtLtPlugin, PrefixPlugin, PhrasePlugin)

import logging
logger = logging.getLogger( __name__ )

default_search_plugins =  (GtLtPlugin, DateParserPlugin, PrefixPlugin, PhrasePlugin)

def create_query_parser(fieldname, schema=None, plugins=default_search_plugins):
	qparser = QueryParser(fieldname, schema=schema)
	for pg in plugins or ():
		qparser.add_plugin(pg())
	return qparser

def parse_subquery(name, value, schema=None, plugins=default_search_plugins, qparser=None):
	result = None
	try:
		qparser = qparser if qparser else create_query_parser(name, schema=schema, plugins=plugins)
		result = qparser.parse(value)
	except:
		result = None
		
	result = result if result is not None else Term(name, value)
	return result
	
def parse_query(fieldname, qo, schema_or_names, plugins=default_search_plugins):
	schema = schema_or_names if isinstance(schema_or_names, fields.Schema) else None	
	main_query = parse_subquery(fieldname, qo.term, schema=schema, plugins=plugins)
	return main_query
