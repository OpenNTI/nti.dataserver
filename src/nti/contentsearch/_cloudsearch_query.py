# -*- coding: utf-8 -*-
"""
CloudSearch query utils

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component

from .common import normalize_type_name
from . import _cloudsearch_interfaces as cloudsearch_interfaces
from .constants import (username_, content_, type_, ngrams_, tags_, title_, invalid_type_,
						redaction_explanation_, replacement_content_, ugd_indexable_type_names)

def adapt_search_on_types(searchOn=None):
	if searchOn:
		result = [normalize_type_name(x) for x in searchOn if x in ugd_indexable_type_names]
		result = result or (invalid_type_)
	else:
		result = ()
	return result

@interface.implementer(cloudsearch_interfaces.ICloudSearchQueryParser)
class _DefaultCloudSearchQueryParser(object):

	def _get_search_fields(self, qo):
		if qo.is_phrase_search or qo.is_prefix_search:
			result = (content_, redaction_explanation_, replacement_content_)
		else:
			result = (ngrams_, title_, tags_, redaction_explanation_, replacement_content_)
		return result

	def parse(self, qo, username=None):
		username = username or qo.username
		searchOn = adapt_search_on_types(qo.searchOn)
		search_fields = self._get_search_fields(qo)

		bq = ['(and']
		bq.append("%s:'%s'" % (username_, username))

		if len(search_fields) > 1:
			bq.append('(or')
			for search_field in search_fields:
				bq.append("%s:'%s'" % (search_field, qo.term))
			bq.append(')')
		else:
			bq.append("%s:'%s'" % (search_fields[0], qo.term))

		if searchOn:
			bq.append('(or')
			for type_name in searchOn:
				bq.append("%s:'%s' " % (type_, type_name))
			bq.append(')')

		bq.append(')')
		result = ' '.join(bq)
		return result

def parse_query(qo, username=None):
	parser = component.getUtility(cloudsearch_interfaces.ICloudSearchQueryParser)
	result = parser.parse(qo, username)
	return result
