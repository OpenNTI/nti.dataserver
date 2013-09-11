#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MongoDB query utils

$Id: _cloudsearch_query.py 19987 2013-06-07 14:43:10Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component

from .common import normalize_type_name
from .constants import ugd_indexable_type_names
from . import _mongodb_interfaces as mongodb_interfaces

def adapt_search_on_types(searchOn=None):
	if searchOn:
		result = [hash(normalize_type_name(x)) for x in searchOn if x in ugd_indexable_type_names]
		result = result or [0]
	else:
		result = []
	return result

@interface.implementer(mongodb_interfaces.IMongoDBQueryParser)
class _DefaultMongoDBQueryParser(object):

	def parse(self, qo):
		searchOn = adapt_search_on_types(qo.searchOn)
		result = {'search': qo.term}
		if searchOn:
			result['filter':{'$in':searchOn}]
		return result

def parse_query(qo, username=None):
	parser = component.getUtility(mongodb_interfaces.IMongoDBQueryParser)
	result = parser.parse(qo)
	return result
