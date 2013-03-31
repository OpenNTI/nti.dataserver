# -*- coding: utf-8 -*-
"""
Cloudsearch index definition.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time
import json
import hashlib
from datetime import datetime

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as for_interfaces

from nti.chatserver import interfaces as chat_interfaces

from .common import get_type_name
from . import interfaces as search_interfaces
from . import _discriminators as discriminators
from . import _cloudsearch_interfaces as cloudsearch_interfaces

from .constants import (CLASS, CREATOR, last_modified_fields, ntiid_fields, INTID, container_id_fields)
from .constants import (ngrams_, channel_, content_, keywords_, references_, username_,
						last_modified_, recipients_, sharedWith_, ntiid_, type_, tags_,
						creator_, containerId_, intid_, title_, redaction_explanation_, replacement_content_,
						redactionExplanation_, replacementContent_)

# define search fields

search_stored_fields = (intid_,)

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

	_shared_with = sharedWith_.lower()
	_container_id = containerId_.lower()

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
								  source_attributes=last_modified_fields)

	connection.define_index_field(domain_name, ntiid_, 'literal', searchable=True, result=False,
								  source_attributes=ntiid_fields)

	connection.define_index_field(domain_name, _container_id, 'literal', searchable=True, result=False,
								  source_attributes=container_id_fields)

	connection.define_index_field(domain_name, username_, 'literal', searchable=True, result=False, facet=True)
	connection.define_index_field(domain_name, channel_, 'literal', searchable=True, result=False, facet=True)

	# content fields
	connection.define_index_field(domain_name, content_, 'text', searchable=True, result=False)
	connection.define_index_field(domain_name, ngrams_, 'text', searchable=True, result=False)
	connection.define_index_field(domain_name, title_, 'text', searchable=True, result=False)
	connection.define_index_field(domain_name, recipients_, 'text', searchable=True, result=False)
	connection.define_index_field(domain_name, _shared_with, 'text', searchable=True, result=False,
								  source_attributes=(sharedWith_,))
	connection.define_index_field(domain_name, replacement_content_, 'text', searchable=True, result=False,
								  source_attributes=(replacementContent_,))
	connection.define_index_field(domain_name, redaction_explanation_, 'text', searchable=True, result=False,
								  source_attributes=(redactionExplanation_,))

	# faceted fields
	connection.define_index_field(domain_name, keywords_, 'text', searchable=True, result=False, facet=True)
	connection.define_index_field(domain_name, references_, 'text', searchable=True, result=False, facet=True)
	connection.define_index_field(domain_name, tags_, 'text', searchable=True, result=False, facet=True)

	# make sure 'content' is the default field if its result=False
	connection.update_default_search_field(domain_name, content_)

	# set the stop word policy
	sw_util = component.queryUtility(search_interfaces.IStopWords)
	stoplist = sw_util.stopwords(language) if sw_util else ()
	stoplist = json.dumps({'stopwords':stoplist})
	connection.update_stopword_options(domain_name, stoplist)

	return domain

def get_cloud_oid(oid):
	return hashlib.sha224(str(oid)).hexdigest()

def get_last_modified(data):
	result = discriminators.get_last_modified(data, time.time())
	result = datetime.fromtimestamp(result)
	result = result.strftime('%Y%m%d%H%M%S')
	return result

def get_post_tags(obj):
	result = discriminators.get_post_tags(obj)
	return unicode(','.join(result)) if result else u''

def get_uid(obj):
	uid = discriminators.get_uid(obj)
	return unicode(uid)

@interface.implementer(cloudsearch_interfaces.ICloudSearchObject)
class _AbstractCSObject(dict):

	def __init__(self, src):
		self._set_items(src)

	def _set_items(self, src):
		self[intid_] = get_uid(src)
		self[type_] = get_type_name(src)
		self[last_modified_] = get_last_modified(src)
		self[creator_] = discriminators.get_creator(src)
		self[ngrams_] = discriminators.get_object_ngrams(src)
		self[content_] = discriminators.get_object_content(src)

@component.adapter(nti_interfaces.INote)
class _CSNote(_AbstractCSObject):
	pass

@component.adapter(nti_interfaces.IHighlight)
class _CSHighlight(_AbstractCSObject):
	pass

@component.adapter(nti_interfaces.IRedaction)
class _CSRedaction(_AbstractCSObject):

	def _set_items(self, src):
		super(_CSRedaction, self)._set_items(src)
		self[replacement_content_] = discriminators.get_replacement_content_and_ngrams(src)
		self[redaction_explanation_] = discriminators.get_redaction_explanation_and_ngrams(src)

@component.adapter(chat_interfaces.IMessageInfo)
class _CSMessageInfo(_AbstractCSObject):
	pass

@component.adapter(for_interfaces.IPost)
class _CSPost(_AbstractCSObject):

	def _set_items(self, src):
		super(_CSPost, self)._set_items(src)
		self[tags_] = get_post_tags(src)
		self[title_] = discriminators.get_post_title(src)

def to_cloud_object(obj, username):
	data = cloudsearch_interfaces.ICloudSearchObject(obj)
	data[username_] = username
	return data
