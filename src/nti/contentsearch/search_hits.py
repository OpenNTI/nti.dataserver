# -*- coding: utf-8 -*-
"""
Defines adapters for search hits

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import uuid
import collections

from zope import component
from zope import interface

from nti.chatserver import interfaces as chat_interfaces

from nti.contentfragments import interfaces as frg_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as for_interfaces

from nti.mimetype.mimetype import nti_mimetype_from_object

from nti.utils.property import alias

from . import discriminators
from . import interfaces as search_interfaces

from .constants import (HIT, CONTENT, OID, POST, BOOK_CONTENT_MIME_TYPE,
						VIDEO_TRANSCRIPT, NTI_CARD, VIDEO_TRANSCRIPT_MIME_TYPE,
						NTI_CARD_MIME_TYPE)

def get_search_hit(obj, score=1.0, query=None):
	hit = search_interfaces.ISearchHit(obj)
	hit.Score = score
	hit.Query = query
	return hit

def get_hit_id(obj):
	if nti_interfaces.IModeledContent.providedBy(obj):
		result = unicode(discriminators.get_uid(obj))
	elif isinstance(obj, collections.Mapping):
		result = obj.get(OID, None)
	else:
		result = unicode(uuid.uuid4())  # generate one
	return result

class _MetaSearchHit(type):

	def __new__(cls, name, bases, dct):
		t = type.__new__(cls, name, bases, dct)
		t.parameters = dict()
		t.mimeType = 'application/vnd.nextthought.search.%s' % name[1:].lower()
		t.mime_type = t.mimeType
		setattr(t, '__external_can_create__', True)
		setattr(t, '__external_class_name__', HIT)
		return t

@interface.implementer(search_interfaces.ISearchHit)
class _BaseSearchHit(object):

	__metaclass__ = _MetaSearchHit

	NTIID = Query = Creator = ContainerId = Snippet = None

	LastModified = alias('lastModified')

	def __init__(self, original, oid=None, score=1.0):
		self.OID = oid
		self.lastModified = 0
		self.set_hit_info(original, score)

	def set_hit_info(self, original, score):
		self.Score = score
		self.Type = original.__class__.__name__
		self.TargetMimeType = nti_mimetype_from_object(original, False) or u''

BaseSearchHit = _BaseSearchHit  # BWC

def get_field_value(obj, name, default=u''):
	result = getattr(obj, name, None)
	return result if result else default

class _SearchHit(_BaseSearchHit):

	adapter_interface = search_interfaces.IUserContentResolver

	def __init__(self, original, score=1.0):
		super(_SearchHit, self).__init__(original, get_hit_id(original), score)

	def set_hit_info(self, original, score):
		super(_SearchHit, self).set_hit_info(original, score)
		adapted = component.getAdapter(original, self.adapter_interface)
		self.Snippet = self.get_snippet(adapted)
		self.NTIID = get_field_value(adapted, 'ntiid')
		self.Creator = get_field_value(adapted, 'creator')
		self.ContainerId = get_field_value(adapted, 'containerId')
		self.lastModified = get_field_value(adapted, 'lastModified', 0)
		return adapted

	@classmethod
	def get_snippet(cls, adapted):
		text = get_field_value(adapted, 'content')
		text = component.getAdapter(text,
									frg_interfaces.IPlainTextContentFragment,
									name='text')
		return text

SearchHit = _SearchHit  # BWC

@component.adapter(nti_interfaces.INote)
@interface.implementer(search_interfaces.INoteSearchHit)
class _NoteSearchHit(_SearchHit):
	adapter_interface = search_interfaces.INoteContentResolver

	title = alias('Title')

	def set_hit_info(self, original, score):
		adapted = super(_NoteSearchHit, self).set_hit_info(original, score)
		self.Title = get_field_value(adapted, 'title')
		return adapted

@component.adapter(nti_interfaces.IHighlight)
@interface.implementer(search_interfaces.IHighlightSearchHit)
class _HighlightSearchHit(_SearchHit):
	adapter_interface = search_interfaces.IHighlightContentResolver

@component.adapter(nti_interfaces.IRedaction)
@interface.implementer(search_interfaces.IRedactionSearchHit)
class _RedactionSearchHit(_SearchHit):

	adapter_interface = search_interfaces.IRedactionContentResolver

	replacementContent = alias('ReplacementContent')
	redactionExplanation = alias('RedactionExplanation')

	def set_hit_info(self, original, score):
		adapted = super(_RedactionSearchHit, self).set_hit_info(original, score)
		self.ReplacementContent = get_field_value(adapted, "replacementContent")
		self.RedactionExplanation = get_field_value(adapted, "redactionExplanation")
		return adapted

@component.adapter(chat_interfaces.IMessageInfo)
@interface.implementer(search_interfaces.IMessageInfoSearchHit)
class _MessageInfoSearchHit(_SearchHit):
	adapter_interface = search_interfaces.IMessageInfoContentResolver

@component.adapter(for_interfaces.IPost)
@interface.implementer(search_interfaces.IPostSearchHit)
class _PostSearchHit(_SearchHit):

	adapter_interface = search_interfaces.IPostContentResolver

	tags = alias('Tags')
	title = alias('Title')

	def set_hit_info(self, original, score):
		adapted = super(_PostSearchHit, self).set_hit_info(original, score)
		self.TYPE = POST
		self.Tags = self.get_tags(adapted)
		self.ID = get_field_value(adapted, "id")
		self.Title = get_field_value(adapted, "title")
		return adapted

	@classmethod
	def get_tags(cls, adapted):
		t = get_field_value(adapted, "tags" , ())
		return unicode(' '.join(t))

@component.adapter(search_interfaces.IWhooshBookContent)
@interface.implementer(search_interfaces.IWhooshBookSearchHit)
class _WhooshBookSearchHit(_BaseSearchHit):

	title = alias('Title')
	content = alias('Snippet')

	def __init__(self, hit):
		super(_WhooshBookSearchHit, self).__init__(hit, oid=self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(_WhooshBookSearchHit, self).set_hit_info(hit, score)
		self.Type = CONTENT
		self.NTIID = hit.ntiid
		self.Title = hit.title
		self.Snippet = hit.content
		self.ContainerId = hit.ntiid
		self.lastModified = hit.lastModified
		self.TargetMimeType = BOOK_CONTENT_MIME_TYPE

	@classmethod
	def get_oid(cls, hit):
		return unicode(hit.ntiid)

@component.adapter(search_interfaces.IWhooshVideoTranscriptContent)
@interface.implementer(search_interfaces.IWhooshVideoTranscriptSearchHit)
class _WhooshVideoTranscriptSearchHit(_BaseSearchHit):

	content = alias('Snippet')

	def __init__(self, hit):
		super(_WhooshVideoTranscriptSearchHit, self).__init__(hit, oid=self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(_WhooshVideoTranscriptSearchHit, self).set_hit_info(hit, score)
		self.Type = VIDEO_TRANSCRIPT
		self.Title = hit.title
		self.NTIID = hit.videoId
		self.Snippet = hit.content
		self.VideoID = hit.videoId
		self.ContainerId = hit.containerId
		self.lastModified = hit.lastModified
		self.EndMilliSecs = hit.end_millisecs
		self.StartMilliSecs = hit.start_millisecs
		self.TargetMimeType = VIDEO_TRANSCRIPT_MIME_TYPE

	@classmethod
	def get_oid(cls, hit):
		result = (unicode(hit.docnum), u'-', unicode(hit.videoId))
		return unicode(''.join(result))

@component.adapter(search_interfaces.IWhooshNTICardContent)
@interface.implementer(search_interfaces.IWhooshNTICardSearchHit)
class _WhooshNTICardSearchHit(_BaseSearchHit):

	title = alias('Title')
	content = alias('Snippet')

	def __init__(self, hit):
		super(_WhooshNTICardSearchHit, self).__init__(hit, oid=self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(_WhooshNTICardSearchHit, self).set_hit_info(hit, score)
		self.Type = NTI_CARD
		self.Href = hit.href
		self.NTIID = hit.ntiid
		self.Title = hit.title
		self.Snippet = hit.content
		self.ContainerId = hit.containerId
		self.TargetNTIID = hit.target_ntiid
		self.lastModified = hit.lastModified
		self.TargetMimeType = NTI_CARD_MIME_TYPE

	@classmethod
	def get_oid(cls, hit):
		return unicode(hit.ntiid)

