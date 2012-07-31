from __future__ import print_function, unicode_literals

from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import (username_, content_, type_)

def adapt_search_on_types(search_on=None):
	if search_on:
		search_on = [normalize_type_name(x) for x in search_on]
		return search_on
	else:
		return ()
	
def parse_query(qo, username, fieldname=content_):
	
	search_on = adapt_search_on_types(qo.search_on)
	
	bq = ['(and']
	bq.append("%s:'%s'" % (username_, username))
	bq.append("%s:'%s'" % (fieldname, qo.term))
	
	if search_on:
		bq.append('(or')
		for type_name in search_on:
			bq.append("%s:'%s'" % (type_, type_name))
		bq.append(')')
		
	bq.append(')')
	result = ' '.join(bq)
	return result
