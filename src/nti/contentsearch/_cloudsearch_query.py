from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.contentsearch.common import normalize_type_name
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.common import (username_, content_, type_)

def adapt_searchon_types(searchon=None):
	if searchon:
		searchon = [normalize_type_name(x) for x in searchon]
		return searchon
	else:
		return ()
	
@interface.implementer(search_interfaces.ICloudSearchQueryParser)
class _DefaultCloudSearchQueryParser(object):
	def parse(self, qo):
		username = qo.username
		
		searchon = adapt_searchon_types(qo.searchon)
		
		bq = ['(and']
		bq.append("%s:'%s'" % (username_, username))
		bq.append("%s:'%s'" % (content_, qo.term))
		
		if searchon:
			bq.append('(or')
			for type_name in searchon:
				bq.append("%s:'%s'" % (type_, type_name))
			bq.append(')')
			
		bq.append(')')
		result = ' '.join(bq)
		return result
	
def parse_query(qo):
	parser = component.queryUtility(search_interfaces.ICloudSearchQueryParser)
	result = parser.parse(qo)
	return result
