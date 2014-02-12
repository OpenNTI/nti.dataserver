#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines adapters for search hits

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import uuid
import collections

from zope import component
from zope import interface

from nti.chatserver import interfaces as chat_interfaces

from nti.contentfragments import interfaces as frg_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as for_interfaces

from nti.externalization.externalization import make_repr

from nti.mimetype.mimetype import nti_mimetype_from_object

from nti.utils.property import alias

from . import discriminators
from . import interfaces as search_interfaces

from .constants import (HIT, CONTENT, OID, POST, BOOK_CONTENT_MIME_TYPE,
						VIDEO_TRANSCRIPT, NTI_CARD, VIDEO_TRANSCRIPT_MIME_TYPE,
						NTI_CARD_MIME_TYPE, FORUM)

def get_search_hit(obj, score=1.0, query=None):
	hit = search_interfaces.ISearchHit(obj)
	hit.Score = score
	hit.Query = query
	return hit

def get_hit_id(obj):
	if obj is None:
		result = None
	elif nti_interfaces.IModeledContent.providedBy(obj) or \
		 nti_interfaces.ITitledContent.providedBy(obj):
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
		t.mimeType = 'application/vnd.nextthought.search.%s' % name.lower()
		t.mime_type = t.mimeType
		setattr(t, '__external_can_create__', True)
		setattr(t, '__external_class_name__', HIT)
		return t

@interface.implementer(search_interfaces.ISearchHit)
class BaseSearchHit(object):

	__metaclass__ = _MetaSearchHit

	Score = lastModified = 0

	Fragments = TargetMimeType = ContainerId = None
	Type = NTIID = Query = Creator = Snippet = None

	createdTime = alias('lastModified')

	def __init__(self, original=None, oid=None, score=1.0):
		self.OID = oid
		if original is not None:
			self.set_hit_info(original, score)

	def set_hit_info(self, original, score):
		self.Score = score
		self.Type = unicode(original.__class__.__name__)
		self.TargetMimeType = unicode(nti_mimetype_from_object(original, False) or u'')

	def clone(self):
		result = self.__class__()
		result.__dict__.update(self.__dict__)
		return result

	__repr__ = make_repr()

	def __eq__(self, other):
		try:
			return self is other or self.OID == other.OID
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.OID)
		return xhash

def get_field_value(obj, name, default=u''):
	result = getattr(obj, name, None)
	if isinstance(result, six.string_types):
		result = unicode(result)
	return result if result else default

class SearchHit(BaseSearchHit):

	adapter_interface = search_interfaces.IUserContentResolver

	def __init__(self, original=None, score=1.0):
		super(SearchHit, self).__init__(original, get_hit_id(original), score)

	def set_hit_info(self, original, score):
		super(SearchHit, self).set_hit_info(original, score)
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

@component.adapter(nti_interfaces.INote)
@interface.implementer(search_interfaces.INoteSearchHit)
class NoteSearchHit(SearchHit):
	adapter_interface = search_interfaces.INoteContentResolver

	Title = None

	title = alias('Title')

	def set_hit_info(self, original, score):
		adapted = super(NoteSearchHit, self).set_hit_info(original, score)
		self.Title = get_field_value(adapted, 'title')
		return adapted

@component.adapter(nti_interfaces.IHighlight)
@interface.implementer(search_interfaces.IHighlightSearchHit)
class HighlightSearchHit(SearchHit):
	adapter_interface = search_interfaces.IHighlightContentResolver

@component.adapter(nti_interfaces.IRedaction)
@interface.implementer(search_interfaces.IRedactionSearchHit)
class RedactionSearchHit(SearchHit):
	adapter_interface = search_interfaces.IRedactionContentResolver

	replacementContent = alias('ReplacementContent')
	redactionExplanation = alias('RedactionExplanation')

	def set_hit_info(self, original, score):
		adapted = super(RedactionSearchHit, self).set_hit_info(original, score)
		self.ReplacementContent = get_field_value(adapted, "replacementContent")
		self.RedactionExplanation = get_field_value(adapted, "redactionExplanation")
		return adapted

@component.adapter(chat_interfaces.IMessageInfo)
@interface.implementer(search_interfaces.IMessageInfoSearchHit)
class MessageInfoSearchHit(SearchHit):
	adapter_interface = search_interfaces.IMessageInfoContentResolver

@component.adapter(for_interfaces.IPost)
@interface.implementer(search_interfaces.IPostSearchHit)
class PostSearchHit(SearchHit):
	adapter_interface = search_interfaces.IPostContentResolver

	Title = ID = Tags = None

	tags = alias('Tags')
	title = alias('Title')

	def set_hit_info(self, original, score):
		adapted = super(PostSearchHit, self).set_hit_info(original, score)
		self.TYPE = POST
		self.Tags = self.get_tags(adapted)
		self.ID = get_field_value(adapted, "id")
		self.Title = get_field_value(adapted, "title")
		return adapted

	@classmethod
	def get_tags(cls, adapted):
		t = get_field_value(adapted, "tags" , ())
		return unicode(' '.join(t))

@component.adapter(for_interfaces.IGeneralForum)
@interface.implementer(search_interfaces.IForumSearchHit)
class ForumSearchHit(SearchHit):
	adapter_interface = search_interfaces.IForumContentResolver

	Title = None

	title = alias('Title')

	def set_hit_info(self, original, score):
		adapted = super(ForumSearchHit, self).set_hit_info(original, score)
		self.TYPE = FORUM
		self.Title = get_field_value(adapted, "title")
		return adapted

@component.adapter(search_interfaces.IWhooshBookContent)
@interface.implementer(search_interfaces.IWhooshBookSearchHit)
class WhooshBookSearchHit(BaseSearchHit):

	Title = None

	title = alias('Title')
	content = alias('Snippet')

	def __init__(self, hit=None):
		super(WhooshBookSearchHit, self).__init__(hit, oid=self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(WhooshBookSearchHit, self).set_hit_info(hit, score)
		self.Type = CONTENT
		self.NTIID = hit.ntiid
		self.Title = hit.title
		self.Snippet = hit.content
		self.ContainerId = hit.ntiid
		self.lastModified = hit.lastModified
		self.TargetMimeType = BOOK_CONTENT_MIME_TYPE

	@classmethod
	def get_oid(cls, hit):
		return unicode(hit.ntiid) if hit is not None else None

@component.adapter(search_interfaces.IWhooshVideoTranscriptContent)
@interface.implementer(search_interfaces.IWhooshVideoTranscriptSearchHit)
class WhooshVideoTranscriptSearchHit(BaseSearchHit):

	VideoID = EndMilliSecs = StartMilliSecs = Title = None

	content = alias('Snippet')

	def __init__(self, hit=None):
		super(WhooshVideoTranscriptSearchHit, self).__init__(hit, oid=self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(WhooshVideoTranscriptSearchHit, self).set_hit_info(hit, score)
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
		if hit is not None:
			result = (unicode(hit.docnum), u'-', unicode(hit.videoId))
			result = unicode(''.join(result))
		else:
			result = None
		return result

@component.adapter(search_interfaces.IWhooshNTICardContent)
@interface.implementer(search_interfaces.IWhooshNTICardSearchHit)
class WhooshNTICardSearchHit(BaseSearchHit):

	TargetNTIID = Title = Href = None

	title = alias('Title')
	content = alias('Snippet')

	def __init__(self, hit=None):
		super(WhooshNTICardSearchHit, self).__init__(hit, oid=self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(WhooshNTICardSearchHit, self).set_hit_info(hit, score)
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
		return unicode(hit.ntiid) if hit is not None else None

