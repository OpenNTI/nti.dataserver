from __future__ import print_function, unicode_literals

import hashlib

from nti.externalization.externalization import toExternalObject

from nti.contentsearch import CaseInsensitiveDict

from nti.contentsearch.common import ngrams
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import get_external_oid
from nti.contentsearch.common import get_note_content
from nti.contentsearch.common import get_last_modified
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import get_highlight_content
from nti.contentsearch.common import get_redaction_content
from nti.contentsearch.common import get_messageinfo_content

from nti.contentsearch.common import (	CLASS, CREATOR, ID, OID, last_modified_fields, ntiid_fields, 
										container_id_fields, NTIID, CONTAINER_ID, TARGET_OID, LAST_MODIFIED)

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_, username_,
										last_modified_, recipients_, sharedWith_, id_, ntiid_, type_,
										oid_, creator_, note_, messageinfo, highlight_, containerId_,
										redaction_)

import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

compute_ngrams = False #TODO: set this as part of a config

# -----------------------------------

mid_ = u'mid'
search_stored_fields=[type_, creator_, last_modified_, ntiid_, containerId_.lower(), mid_, oid_, content_]
search_faceted_fields = [keywords_, recipients_, references_, sharedWith_.lower()]
search_indexed_fields = search_stored_fields + search_faceted_fields + [username_, channel_, ngrams_]
												
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
	
	domain.create_index_field(mid_, 'literal', searchable=True, result=True, 
							  source_attributes=(id_, ID))
	
	domain.create_index_field(oid_, 'literal', searchable=True, result=True,
							  source_attributes=(oid_, OID, TARGET_OID))
	
	domain.create_index_field(content_, 'text', searchable=True, result=True)
		
	# literal fields
	domain.create_index_field(username_, 'literal', searchable=True, result=False, facet=True)
	domain.create_index_field(channel_, 'literal', searchable=True, result=False, facet=True)
	
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

# create field mappings from cloud to search_hit
cloud2hit_field_mappings = CaseInsensitiveDict()
cloud2hit_field_mappings[type_] 		= CLASS
cloud2hit_field_mappings[creator_]		= CREATOR
cloud2hit_field_mappings[ntiid_]		= NTIID 
cloud2hit_field_mappings[containerId_]	= CONTAINER_ID
cloud2hit_field_mappings[mid_]			= ID
cloud2hit_field_mappings[oid_]			= TARGET_OID
cloud2hit_field_mappings[sharedWith_]	= sharedWith_
for name in last_modified_fields:
	cloud2hit_field_mappings[name] = LAST_MODIFIED
			
# create search_hit to cloud
ds2cloud_field_mappings = {}
for n,v in cloud2hit_field_mappings.items():
	ds2cloud_field_mappings[v] = n.lower()

# special cases
ds2cloud_field_mappings.pop(TARGET_OID, None)
ds2cloud_field_mappings[OID] = oid_
ds2cloud_field_mappings[LAST_MODIFIED] = last_modified_

# -----------------------------------

def get_cloud_oid(obj):
	oid = get_external_oid(obj)
	return hashlib.sha224(oid).hexdigest()

def get_object_content(data, type_name=None):
	type_name = normalize_type_name(type_name or get_type_name(data))
	if type_name == note_:
		result = get_note_content(data)
	elif type_name == highlight_:
		result = get_highlight_content(data)
	elif type_name == redaction_:
		result = get_redaction_content(data)
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
	oid  = get_cloud_oid(obj)
	data = toExternalObject(obj)
		
	# make sure we remove fields that are not to be indexed
	for n in list(data.keys()):
		if n in ds2cloud_field_mappings:
			value = data.pop(n)
			k = ds2cloud_field_mappings[n]
			data[k] = value
		else:
			data.pop(n)
		
	# we need to normalize the type
	data[type_] = normalize_type_name(data[type_])
	
	# make sure the user name is always set
	data[username_] = username
		
	# set content
	data[content_] = get_object_content(obj, type_name)
	if compute_ngrams:
		data[ngrams_] = get_object_ngrams(obj, type_name)
		
	# get and update the last modified data
	# cs supports uint ony and we use this number as version also
	lm = int(get_last_modified(data)) 
	data[last_modified_] = lm
				
	return oid, data

def to_external_dict(cloud_data):
	# aws seems to return item results in a list
	for k in cloud_data.keys():
		v = cloud_data[k]
		if v not in search_faceted_fields and isinstance(v, (list, tuple)):
			cloud_data[k] = v[0] if v else u''
			
	# map ext fields from cloud fields
	for n, k in cloud2hit_field_mappings.items():
		if n in cloud_data:
			v = cloud_data.pop(n)
			if k == CLASS and v:
				v = v.title()
			cloud_data[k] = v
	return cloud_data
