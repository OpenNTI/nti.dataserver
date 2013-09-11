# -*- coding: utf-8 -*-
"""
MongoDB index definition.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as for_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.externalization import externalization

from . import _discriminators as discriminators
from . import _mongodb_interfaces as mongodb_interfaces

from .constants import (_id, ngrams_, content_, last_modified_, tags_,
						creator_, title_, redaction_explanation_, replacement_content_)

def get_uid(obj):
	uid = discriminators.get_uid(obj)
	return unicode(uid)

@interface.implementer(mongodb_interfaces.IMongoDBObject)
class _AbstractMongoDBObject(externalization.LocatedExternalDict):

	def __init__(self, src):
		self._set_items(src)

	def _set_items(self, src):
		self[_id] = get_uid(src)
		self[tags_] = discriminators.get_tags(src)
		self[creator_] = discriminators.get_creator(src)
		self[ngrams_] = discriminators.get_object_ngrams(src)
		self[content_] = discriminators.get_object_content(src)
		self[last_modified_] = discriminators.get_last_modified(src, time.time())

	def toJSON(self):
		result = externalization.to_json_representation(self)
		return result

@component.adapter(nti_interfaces.INote)
class _MDBNote(_AbstractMongoDBObject):
	def _set_items(self, src):
		super(_MDBPost, self)._set_items(src)
		self[title_] = discriminators.get_note_title(src)

@component.adapter(nti_interfaces.IHighlight)
class _MDBHighlight(_AbstractMongoDBObject):
	pass

@component.adapter(nti_interfaces.IRedaction)
class _MDBRedaction(_AbstractMongoDBObject):

	def _set_items(self, src):
		super(_MDBRedaction, self)._set_items(src)
		self[replacement_content_] = discriminators.get_replacement_content_and_ngrams(src)
		self[redaction_explanation_] = discriminators.get_redaction_explanation_and_ngrams(src)

@component.adapter(chat_interfaces.IMessageInfo)
class _MDBMessageInfo(_AbstractMongoDBObject):	
	def _set_items(self, src):
		super(_MDBMessageInfo, self)._set_items(src)
		del self[tags_]
		
@component.adapter(for_interfaces.IPost)
class _MDBPost(_AbstractMongoDBObject):

	def _set_items(self, src):
		super(_MDBPost, self)._set_items(src)
		self[title_] = discriminators.get_post_title(src)

def to_mongodb_object(obj):
	data = mongodb_interfaces.IMongoDBObject(obj)
	return data
