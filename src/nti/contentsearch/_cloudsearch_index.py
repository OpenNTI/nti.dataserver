from nti.externalization.oids import toExternalOID
from nti.externalization.externalization import toExternalObject

from nti.contentsearch import CaseInsensitiveDict

from nti.contentsearch.common import ngrams
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import get_note_content
from nti.contentsearch.common import get_last_modified
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import get_highlight_content
from nti.contentsearch.common import get_messageinfo_content

from nti.contentsearch.common import (	CLASS, CREATOR, ID, OID, last_modified_fields, ntiid_fields, 
										container_id_fields, NTIID, CONTAINER_ID, TARGET_OID, LAST_MODIFIED)

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_, username_,
										last_modified_, recipients_, sharedWith_, id_, ntiid_, type_,
										oid_, creator_, note_, messageinfo, highlight_, containerId_)

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

compute_ngrams = False #TODO: set this as part of a config

# -----------------------------------

stored_fields=[type_, creator_, last_modified_, ntiid_, containerId_.lower(), id_, oid_, content_]

def create_search_domain(connection, domain_name='ntisearch', allow_ips=()):
	
	domain = connection.create_domain(domain_name)
	for ip in allow_ips:
		domain.allow_ip(ip)
		
	# following should be storable fields
	# type, creator, oid, last modified, ntiid, containerId, content, id

	domain.create_index_field(type_, 'literal', searchable=True, result=True,
							  source_attributes=(type_, CLASS))
	
	domain.create_index_field(creator_, 'literal', searchable=True, result=True, 
							  source_attributes=(creator_, CREATOR))
	
	domain.create_index_field(last_modified_, 'uint', searchable=True, result=True,
							  source_attributes=last_modified_fields, default=0 )
	
	domain.create_index_field(ntiid_, 'literal', searchable=True, result=True, 
							  source_attributes=ntiid_fields)
	
	domain.create_index_field(containerId_.lower(), 'literal', searchable=True, result=True,
							  source_attributes=container_id_fields)
	
	domain.create_index_field(id_, 'literal', searchable=True, result=True, 
							  source_attributes=(id_, ID))
	
	domain.create_index_field(oid_, 'literal', searchable=True, result=True,
							  source_attributes=(oid_, OID, TARGET_OID))
	
	domain.create_index_field(content_, 'text', searchable=True, result=True)
		
	# literal fields
	domain.create_index_field(username_, 'literal', searchable=False, result=False)
	domain.create_index_field(channel_, 'literal', searchable=True, result=False)
	
	# faceted fields
	domain.create_index_field(keywords_, 'text', searchable=True, result=False, facet=True)
	domain.create_index_field(recipients_, 'text', searchable=True, result=False, facet=True)
	domain.create_index_field(references_, 'text', searchable=True, result=False, facet=True)
	domain.create_index_field(sharedWith_.lower(), 'text', searchable=True, result=False, facet=True,
							  source_attributes=(sharedWith_,))
	
	# content fields
	domain.create_index_field(ngrams_, 'text', searchable=True, result=False)

	# make sure 'content' is the default field if its result=False
	# connection.update_default_search_field(domain_name, content_)
	
	return domain

# -----------------------------------

_field_mappings = CaseInsensitiveDict()
_field_mappings[type_] 			= CLASS
_field_mappings[creator_]		= CREATOR
_field_mappings[ntiid_]			= NTIID 
_field_mappings[containerId_]	= CONTAINER_ID
_field_mappings[id_]			= ID
_field_mappings[oid_]			= TARGET_OID
_field_mappings[sharedWith_]	= sharedWith_
for name in last_modified_fields:
	_field_mappings[name] = LAST_MODIFIED
			
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

def to_cloud_object(obj, username, type_name):
	oid  = toExternalOID(obj)
	data = toExternalObject(obj)
		
	# make sure the user name is always set
	data[username_] = username
		
	# set content
	data[content_] = get_object_content(obj, type_name)
	if compute_ngrams:
		data[ngrams_] = get_object_ngrams(obj, type_name)
			
	# get and update the last modified data
	# cs supports uint ony and we use this number as version also
	lm = int(get_last_modified(data)) 
	data[LAST_MODIFIED] = lm
		
	return oid, data

def to_search_hit(data):
	for n, k in _field_mappings.items():
		if n in data:
			v = data.pop(n)
			data[k] = v
	return data
