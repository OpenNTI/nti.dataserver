import os
import socket

from nti.contentsearch.exfm.cloudsearch import connect_cloudsearch

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_, username_,
										last_modified_, ntiid_, recipients_, sharedWith_, id_,
										oid_, creator_, containerId_, )

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'AKIAJ42UUP2EUMCMCZIQ')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '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')
		
def create_domain(domain_name, allow_ips=(), access_key=AWS_ACCESS_KEY_ID, secret_key=AWS_SECRET_ACCESS_KEY):
	
	conn = connect_cloudsearch(access_key, secret_key)
	domain = conn.create_domain(domain_name) 
	if not allow_ips:
		allow_ips = socket.gethostbyname_ex(socket.gethostname())[2]
	for ip in allow_ips:
		domain.allow_ip(ip)
		
	# liternal fields
	domain.create_index_field(username_, 'literal', searchable=False, result=False)
	domain.create_index_field(creator_, 'literal', searchable=False, result=False)
	domain.create_index_field(ntiid_, 'literal', searchable=True, result=True)
	domain.create_index_field(oid_, 'literal', searchable=True, result=True)
	domain.create_index_field(id_, 'literal', searchable=True, result=False)
	domain.create_index_field(channel_, 'literal', searchable=True, result=False)
	domain.create_index_field(containerId_, 'literal', searchable=True, result=False)
	
	# faceted fields
	domain.create_index_field(keywords_, 'text', searchable=True, result=False, facet=True)
	domain.create_index_field(sharedWith_, 'text', searchable=True, result=False, facet=True)
	domain.create_index_field(recipients_, 'text', searchable=True, result=False, facet=True)
	domain.create_index_field(references_, 'text', searchable=True, result=False, facet=True)
	
	# uint fields
	domain.create_index_field(last_modified_, 'uint', searchable=True, result=True)
	
	# content fields
	domain.create_index_field(ngrams_, 'text', searchable=True, result=False)
	domain.create_index_field(content_, 'text', searchable=True, result=True)
	
