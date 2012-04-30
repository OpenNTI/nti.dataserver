import os
import socket

from nti.contentsearch.exfm.cloudsearch import connect_cloudsearch

from nti.contentsearch.common import ngrams
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import get_note_content
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import get_highlight_content
from nti.contentsearch.common import get_messageinfo_content

from nti.contentsearch.common import (	CLASS, CREATOR, ID, OID, last_modified_fields, ntiid_fields, 
										container_id_fields, NTIID, CONTAINER_ID, TARGET_OID )

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_, username_,
										last_modified_, recipients_, sharedWith_, id_,
										oid_, creator_, note_, messageinfo, highlight_)

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'AKIAJ42UUP2EUMCMCZIQ')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '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')
		
connect = connect_cloudsearch # alias

def create_domain(connection, domain_name, allow_ips=()):
	
	domain = connection.create_domain(domain_name) 
	if not allow_ips:
		allow_ips = socket.gethostbyname_ex(socket.gethostname())[2]
	for ip in allow_ips:
		domain.allow_ip(ip)
		
	# following should be storable fields
	# type, creator, oid, last modified, ntiid, containerId, content, id
	
	domain.create_index_field(CLASS, 'literal', searchable=True, result=True)
	
	domain.create_index_field(CREATOR, 'literal', searchable=True, result=True, 
							  source_attributes=(creator_, CREATOR))
	
	domain.create_index_field(last_modified_, 'uint', searchable=True, result=True,
							  source_attributes=last_modified_fields )
	
	domain.create_index_field(NTIID, 'literal', searchable=True, result=True, 
							  source_attributes=ntiid_fields)
	
	domain.create_index_field(CONTAINER_ID, 'literal', searchable=True, result=True,
							  source_attributes=container_id_fields)
	
	domain.create_index_field(ID, 'literal', searchable=True, result=True, 
							  source_attributes=(id_, ID))
	
	domain.create_index_field(TARGET_OID, 'literal', searchable=True, result=True,
							  source_attributes=(oid_, OID, TARGET_OID))
	
	domain.create_index_field(content_, 'text', searchable=True, result=True)
		
	# literal fields
	domain.create_index_field(username_, 'literal', searchable=False, result=False)
	domain.create_index_field(channel_, 'literal', searchable=True, result=False)
	
	# faceted fields
	domain.create_index_field(keywords_, 'text', searchable=True, result=False, facet=True)
	domain.create_index_field(sharedWith_, 'text', searchable=True, result=False, facet=True)
	domain.create_index_field(recipients_, 'text', searchable=True, result=False, facet=True)
	domain.create_index_field(references_, 'text', searchable=True, result=False, facet=True)
	
	# content fields
	domain.create_index_field(ngrams_, 'text', searchable=True, result=False)

	# make sure 'content' is the default field
	domain.update_default_search_field(domain_name, content_)
	
	return domain

# -----------------------------------

def get_object_content(data, type_name=None):
	type_name = normalize_type_name(type_name or get_type_name(data))
	if type_name == note_:
		result = get_note_content(data)
	elif type_name == highlight_:
		result = get_highlight_content(data)
	elif type_name == messageinfo:
		result = get_messageinfo_content(data)
	else:
		result = u''
	return result.lower() if result else None

def get_object_ngrams(data, type_name=None):
	content = get_object_content(data, type_name)
	result = ngrams(content)
	return result

