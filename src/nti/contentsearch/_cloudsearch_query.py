from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.contentsearch.common import normalize_type_name
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.common import (username_, content_, type_, ngrams_)

def adapt_searchOn_types(searchOn=None):
	if searchOn:
		searchOn = [normalize_type_name(x) for x in searchOn]
		return searchOn
	else:
		return ()
	
@interface.implementer(search_interfaces.ICloudSearchQueryParser)
class _DefaultCloudSearchQueryParser(object):
	
	def _get_search_fields(self, qo):
		result = (content_,) if qo.is_phrase_search or qo.is_prefix_search else (ngrams_,)
		return result
	
	def parse(self, qo, username=None):
		username = username or qo.username
		searchOn = adapt_searchOn_types(qo.searchOn)
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
	parser = component.getUtility(search_interfaces.ICloudSearchQueryParser)
	result = parser.parse(qo, username)
	return result
