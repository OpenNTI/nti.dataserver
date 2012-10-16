from __future__ import print_function, unicode_literals

import time
import json
import hashlib
from datetime import datetime

import zope.intid
from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.contentsearch import interfaces as search_interfaces

from nti.contentsearch._ngrams_utils import ngrams
from nti.contentsearch.common import get_type_name

from nti.contentsearch.common import (	CLASS, CREATOR, last_modified_fields, ntiid_fields, INTID, 
										container_id_fields)

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_, username_,
										last_modified_, recipients_, sharedWith_, ntiid_, type_,
										creator_, containerId_, intid_) 

import logging
logger = logging.getLogger( __name__ )

# define search fields

_shared_with = sharedWith_.lower()
_container_id = containerId_.lower()

search_stored_fields =  (intid_,)

search_common_fields = (type_, creator_, last_modified_, ntiid_, _container_id,  content_,
						_shared_with, recipients_, ngrams_)

search_faceted_fields = (keywords_, references_, username_, channel_ )

search_indexed_fields = search_stored_fields + search_common_fields + search_faceted_fields 
		
def create_domain(domain_name='ntisearch', aws_access_key_id=None, aws_secret_access_key=None, **kwargs):
	params = {'aws_access_key_id':aws_access_key_id, 'aws_secret_access_key':aws_secret_access_key}
	params.update(kwargs)
	
	# connect to first region
	from boto.cloudsearch import regions, connect_to_region
	region = regions()[0]
	connection = connect_to_region(region.name, **params)
	
	# create domain
	result = create_search_domain(connection, domain_name)
	return result
						
def create_search_domain(connection, domain_name='ntisearch', language='en'):
	
	domain = connection.create_domain(domain_name)
		
	# storable
	connection.define_index_field(domain_name, intid_, 'literal', searchable=False, result=True,
							 	  source_attributes=(INTID, intid_))
		
	# literal
	connection.define_index_field(domain_name, type_, 'literal', searchable=True, result=False,
							 	  source_attributes=(type_, CLASS))
	
	connection.define_index_field(domain_name, creator_, 'literal', searchable=True, result=False, 
								  source_attributes=(creator_, CREATOR))
	
	connection.define_index_field(domain_name, last_modified_, 'text', searchable=True, result=False,
								  source_attributes=last_modified_fields )
	
	connection.define_index_field(domain_name, ntiid_, 'literal', searchable=True, result=False, 
								  source_attributes=ntiid_fields)
	
	connection.define_index_field(domain_name, _container_id, 'literal', searchable=True, result=False,
								  source_attributes=container_id_fields)
		
	connection.define_index_field(domain_name, username_, 'literal', searchable=True, result=False, facet=True)
	connection.define_index_field(domain_name, channel_, 'literal', searchable=True, result=False, facet=True)
	
	# content fields
	connection.define_index_field(domain_name, content_, 'text', searchable=True, result=False)
	connection.define_index_field(domain_name, ngrams_, 'text', searchable=True, result=False)
	
	connection.define_index_field(domain_name, recipients_, 'text', searchable=True, result=False)
	connection.define_index_field(domain_name, _shared_with, 'text', searchable=True, result=False, source_attributes=(sharedWith_,))

	# faceted fields
	connection.define_index_field(domain_name, keywords_, 'text', searchable=True, result=False, facet=True)
	connection.define_index_field(domain_name, references_, 'text', searchable=True, result=False, facet=True)

	# make sure 'content' is the default field if its result=False
	connection.update_default_search_field(domain_name, content_)
	
	# set the stop word policy
	sw_util = component.queryUtility(search_interfaces.IStopWords) 
	stoplist = sw_util.stopwords(language) if sw_util else ()
	stoplist = json.dumps({'stopwords':stoplist})
	connection.update_stopword_options(domain_name, stoplist)
	
	return domain

def get_cloud_oid(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	oid = adapted.get_external_oid()
	return hashlib.sha224(oid).hexdigest()

def get_object_content(data):
	adapted = component.getAdapter(data, search_interfaces.IContentResolver)
	result = adapted.get_content()
	return result.lower() if result else u''

def get_object_ngrams(obj):
	content = get_object_content(obj)
	n_grams = ngrams(content) if content else u''
	result = n_grams if n_grams else u''
	return result

def get_last_modified(data):
	adapted = component.getAdapter(data, search_interfaces.IContentResolver)
	result = adapted.get_last_modified() or time.time()
	result = datetime.fromtimestamp(result)
	result = result.strftime('%Y%m%d%H%M%S')
	return result

def get_channel(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_channel() or u''

def get_containerId(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_containerId() or u''

def get_ntiid(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_ntiid() or u''

def get_creator(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_creator() or unicode(nti_interfaces.SYSTEM_USER_NAME)

def get_recipients(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_recipients()
	return unicode(' '.join(result)) if result else u''

def get_sharedWith(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_sharedWith()
	return unicode(' '.join(result)) if result else u''

def get_references(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_references()
	return unicode(','.join(result)) if result else u''

def get_keywords(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	words = adapted.get_keywords()
	return unicode(','.join(words)) if words else u''

def get_uid(obj):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	uid = _ds_intid.getId(obj)
	return unicode(repr(uid))
	
@interface.implementer(search_interfaces.ICloudSearchObject)
class _AbstractCSObject(dict):
	def __init__( self, src ):
		self._set_items(src)
	
	def _set_items(self, src):
		self[intid_] = get_uid(src)
		self[type_] = get_type_name(src)
		self[creator_] = get_creator(src)
		self[content_] = get_object_content(src)
		self[ngrams_] = get_object_ngrams(src)
		
@component.adapter(nti_interfaces.INote)	
class _CSNote(_AbstractCSObject):
	def _set_items(self, src):
		super(_CSNote, self)._set_items(src)

@component.adapter(nti_interfaces.IHighlight)	
class _CSHighlight(_AbstractCSObject):
	pass

@component.adapter(nti_interfaces.IRedaction)	
class _CSRedaction(_AbstractCSObject):
	pass

@component.adapter(chat_interfaces.IMessageInfo)	
class _CSMessageInfo(_AbstractCSObject):
	def _set_items(self, src):
		super(_CSMessageInfo, self)._set_items(src)

def to_cloud_object(obj, username):
	oid = get_cloud_oid(obj)
	data = search_interfaces.ICloudSearchObject(obj)
	data[username_] = username
	return oid, data

