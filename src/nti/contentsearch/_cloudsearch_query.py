from __future__ import print_function, unicode_literals

from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import (username_, content_, type_)

def adapt_searchon_types(searchon=None):
	if searchon:
		searchon = [normalize_type_name(x) for x in searchon]
		return searchon
	else:
		return ()
	
def parse_query(qo, username, fieldname=content_):
	
	searchon = adapt_searchon_types(qo.searchon)
	
	bq = ['(and']
	bq.append("%s:'%s'" % (username_, username))
	bq.append("%s:'%s'" % (fieldname, qo.term))
	
	if searchon:
		bq.append('(or')
		for type_name in searchon:
			bq.append("%s:'%s'" % (type_, type_name))
		bq.append(')')
		
	bq.append(')')
	result = ' '.join(bq)
	return result
