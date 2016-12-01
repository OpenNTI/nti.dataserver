#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines adapters for search hits

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import uuid
import collections

from zope import component
from zope import interface

from zope.location.interfaces import IContained

from nti.chatserver.interfaces import IMessageInfo

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IHighlight
from nti.dataserver.interfaces import IRedaction
from nti.dataserver.interfaces import ITitledContent
from nti.dataserver.interfaces import IModeledContent
from nti.dataserver.interfaces import SYSTEM_USER_NAME
from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForum
from nti.dataserver.contenttypes.forums.interfaces import IHeadlineTopic

from nti.externalization.representation import WithRepr

from nti.mimetype.mimetype import nti_mimetype_from_object

from nti.property.property import alias

from .discriminators import get_uid

from .interfaces import ISearchHit
from .interfaces import INoteSearchHit
from .interfaces import IPostSearchHit
from .interfaces import IForumSearchHit
from .interfaces import IWhooshBookContent
from .interfaces import IHighlightSearchHit
from .interfaces import IRedactionSearchHit
from .interfaces import INoteContentResolver
from .interfaces import IPostContentResolver
from .interfaces import IUserContentResolver
from .interfaces import IWhooshBookSearchHit
from .interfaces import IForumContentResolver
from .interfaces import IMessageInfoSearchHit
from .interfaces import IWhooshNTICardContent
from .interfaces import IWhooshNTICardSearchHit
from .interfaces import IHighlightContentResolver
from .interfaces import IRedactionContentResolver
from .interfaces import IMessageInfoContentResolver
from .interfaces import IWhooshAudioTranscriptContent
from .interfaces import IWhooshVideoTranscriptContent
from .interfaces import IWhooshAudioTranscriptSearchHit
from .interfaces import IWhooshVideoTranscriptSearchHit

from .constants import VIDEO_TRANSCRIPT, NTI_CARD, VIDEO_TRANSCRIPT_MIME_TYPE
from .constants import HIT, CONTENT, OID, POST, BOOK_CONTENT_MIME_TYPE, FORUM
from .constants import AUDIO_TRANSCRIPT, AUDIO_TRANSCRIPT_MIME_TYPE, NTI_CARD_MIME_TYPE

def get_search_hit(obj, score=1.0, query=None):
	hit = ISearchHit(obj)
	hit.Score = score
	hit.Query = query
	return hit
create_search_hit = get_search_hit # alias BWC

def get_hit_id(obj):
	if obj is None:
		result = None
	elif IModeledContent.providedBy(obj) or \
		 ITitledContent.providedBy(obj):
		result = unicode(get_uid(obj))
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

@interface.implementer(ISearchHit, IContained)
@WithRepr
class BaseSearchHit(object):

	__metaclass__ = _MetaSearchHit

	__parent__ = None
	__name__ = alias('OID')

	Target = None
	Score = lastModified = 0

	Creator = SYSTEM_USER_NAME
	Type = NTIID = Query = Snippet = None
	Fragments = TargetMimeType = ContainerId = None
	
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
		result.__parent__ = None
		return result

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

	ID = alias('OID')

	adapter_interface = IUserContentResolver

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
		text = component.getAdapter(text, IPlainTextContentFragment, name='text')
		return text

@component.adapter(INote)
@interface.implementer(INoteSearchHit)
class NoteSearchHit(SearchHit):
	adapter_interface = INoteContentResolver

	Title = None

	title = alias('Title')

	def set_hit_info(self, original, score):
		adapted = super(NoteSearchHit, self).set_hit_info(original, score)
		self.Title = get_field_value(adapted, 'title')
		return adapted

@component.adapter(IHighlight)
@interface.implementer(IHighlightSearchHit)
class HighlightSearchHit(SearchHit):
	adapter_interface = IHighlightContentResolver

@component.adapter(IRedaction)
@interface.implementer(IRedactionSearchHit)
class RedactionSearchHit(SearchHit):
	adapter_interface = IRedactionContentResolver

	replacementContent = alias('ReplacementContent')
	redactionExplanation = alias('RedactionExplanation')

	def set_hit_info(self, original, score):
		adapted = super(RedactionSearchHit, self).set_hit_info(original, score)
		self.ReplacementContent = get_field_value(adapted, "replacementContent")
		self.RedactionExplanation = get_field_value(adapted, "redactionExplanation")
		return adapted

@component.adapter(IMessageInfo)
@interface.implementer(IMessageInfoSearchHit)
class MessageInfoSearchHit(SearchHit):
	adapter_interface = IMessageInfoContentResolver

@component.adapter(IPost)
@interface.implementer(IPostSearchHit)
class PostSearchHit(SearchHit):
	adapter_interface = IPostContentResolver

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

@component.adapter(IHeadlineTopic)
class HeadlineTopicSearchHit(PostSearchHit):

	def __init__(self, original=None, score=1.0):
		original = getattr(original, 'headline', None)
		super(HeadlineTopicSearchHit, self).__init__(original, score)

@component.adapter(IGeneralForum)
@interface.implementer(IForumSearchHit)
class ForumSearchHit(SearchHit):
	adapter_interface = IForumContentResolver

	Title = None

	title = alias('Title')

	def set_hit_info(self, original, score):
		adapted = super(ForumSearchHit, self).set_hit_info(original, score)
		self.TYPE = FORUM
		self.Title = get_field_value(adapted, "title")
		return adapted

@component.adapter(IWhooshBookContent)
@interface.implementer(IWhooshBookSearchHit)
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

class WhooshMediaTranscriptSearchHit(BaseSearchHit):

	TRANSCRIPT_TYPE = None
	TRANSCRIPT_MIME_TYPE = None
	EndMilliSecs = StartMilliSecs = Title = None

	content = alias('Snippet')

	def __init__(self, hit=None):
		super(WhooshMediaTranscriptSearchHit, self).__init__(hit, oid=self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(WhooshMediaTranscriptSearchHit, self).set_hit_info(hit, score)
		self.Title = hit.title
		self.Snippet = hit.content
		self.Type = self.TRANSCRIPT_TYPE
		self.ContainerId = hit.containerId
		self.lastModified = hit.lastModified
		self.EndMilliSecs = hit.end_millisecs
		self.StartMilliSecs = hit.start_millisecs
		self.TargetMimeType = self.TRANSCRIPT_MIME_TYPE

@component.adapter(IWhooshVideoTranscriptContent)
@interface.implementer(IWhooshVideoTranscriptSearchHit)
class WhooshVideoTranscriptSearchHit(WhooshMediaTranscriptSearchHit):

	VideoID = None
	TRANSCRIPT_TYPE = VIDEO_TRANSCRIPT
	TRANSCRIPT_MIME_TYPE = VIDEO_TRANSCRIPT_MIME_TYPE

	def __init__(self, hit=None):
		super(WhooshVideoTranscriptSearchHit, self).__init__(hit)

	def set_hit_info(self, hit, score):
		super(WhooshVideoTranscriptSearchHit, self).set_hit_info(hit, score)
		self.VideoID = self.NTIID = hit.videoId

	@classmethod
	def get_oid(cls, hit):
		if hit is not None:
			result = (unicode(hit.docnum), u'-', unicode(hit.videoId))
			result = unicode(''.join(result))
		else:
			result = None
		return result

@component.adapter(IWhooshAudioTranscriptContent)
@interface.implementer(IWhooshAudioTranscriptSearchHit)
class WhooshAudioTranscriptSearchHit(WhooshMediaTranscriptSearchHit):

	AudioID = None
	TRANSCRIPT_TYPE = AUDIO_TRANSCRIPT
	TRANSCRIPT_MIME_TYPE = AUDIO_TRANSCRIPT_MIME_TYPE

	def __init__(self, hit=None):
		super(WhooshAudioTranscriptSearchHit, self).__init__(hit)

	def set_hit_info(self, hit, score):
		super(WhooshVideoTranscriptSearchHit, self).set_hit_info(hit, score)
		self.AudioID = self.NTIID = hit.audioId

	@classmethod
	def get_oid(cls, hit):
		if hit is not None:
			result = (unicode(hit.docnum), u'-', unicode(hit.audioId))
			result = unicode(''.join(result))
		else:
			result = None
		return result

class TranscriptSearchHit(WhooshVideoTranscriptSearchHit):
	pass

@component.adapter(IWhooshNTICardContent)
@interface.implementer(IWhooshNTICardSearchHit)
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
