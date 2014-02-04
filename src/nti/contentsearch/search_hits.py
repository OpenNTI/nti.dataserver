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

from .constants import (title_)
from .constants import (NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
						SNIPPET, HIT, ID, CONTENT, SCORE, OID, POST, MIME_TYPE,
						VIDEO_ID, BOOK_CONTENT_MIME_TYPE, VIDEO_TRANSCRIPT,
						NTI_CARD, TITLE, HREF, VIDEO_TRANSCRIPT_MIME_TYPE,
						START_MILLISECS, END_MILLISECS, NTI_CARD_MIME_TYPE,
						TARGET_NTIID, TARGET_MIME_TYPE)

def get_search_hit(obj, score=1.0, query=None):
	hit = search_interfaces.ISearchHit(obj)
	hit.score = score
	hit.query = query
	return hit

def _get_hit_id(obj):
	if nti_interfaces.IModeledContent.providedBy(obj):
		result = unicode(discriminators.get_uid(obj))
	elif isinstance(obj, collections.Mapping):
		result = obj.get(OID, None)
	else:
		result = None
	return result or unicode(uuid.uuid4())

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
class _BaseSearchHit(dict):

	__metaclass__ = _MetaSearchHit

	oid = alias('OID')

	def __init__(self, original, oid=None, score=1.0):
		self.OID = oid
		self._query = None
		self.set_hit_info(original, score)

	def set_hit_info(self, original, score):
		self[CLASS] = HIT
		self[SCORE] = score
		self[MIME_TYPE] = self.mimeType
		self[TYPE] = original.__class__.__name__
		self[TARGET_MIME_TYPE] = nti_mimetype_from_object(original, False) or u''

	def get_query(self):
		return self._query

	def set_query(self, query):
		self._query = search_interfaces.ISearchQuery(query, None)

	Query = query = property(get_query, set_query)

	def get_score(self):
		return self.get(SCORE, 1.0)

	def set_score(self, score=1.0):
		self[SCORE] = score or 1.0

	Score = score = property(get_score, set_score)

	@property
	def Type(self):
		return self.get(TYPE)

	@property
	def NTIID(self):
		return self.get(NTIID)

	@property
	def lastModified(self):
		return self.get(LAST_MODIFIED, 0)
	last_modified = lastModified

BaseSearchHit = _BaseSearchHit  # BWC

def get_value(obj, name, default=u''):
	result = getattr(obj, name, None)
	return result if result else default

class _SearchHit(_BaseSearchHit):

	adapter_interface = search_interfaces.IUserContentResolver

	def __init__(self, original, score=1.0):
		super(_SearchHit, self).__init__(original, _get_hit_id(original), score)

	def set_hit_info(self, original, score):
		super(_SearchHit, self).set_hit_info(original, score)
		adapted = component.queryAdapter(original, self.adapter_interface)
		self[SNIPPET] = self.get_snippet(adapted)
		self[NTIID] = get_value(adapted, 'ntiid')
		self[CREATOR] = get_value(adapted, 'creator')
		self[CONTAINER_ID] = get_value(adapted, 'containerId')
		self[LAST_MODIFIED] = get_value(adapted, 'lastModified', 0)
		return adapted

	@classmethod
	def get_snippet(cls, adapted):
		text = get_value(adapted, 'content')
		text = component.getAdapter(text,
									frg_interfaces.IPlainTextContentFragment,
									name='text')
		return text

SearchHit = _SearchHit  # BWC

@component.adapter(nti_interfaces.INote)
@interface.implementer(search_interfaces.INoteSearchHit)
class _NoteSearchHit(_SearchHit):
	adapter_interface = search_interfaces.INoteContentResolver

	Title = alias('title')

	def set_hit_info(self, original, score):
		adapted = super(_NoteSearchHit, self).set_hit_info(original, score)
		self.title = get_value(adapted, 'title')
		return adapted

	def get_title(self):
		return self.title

@component.adapter(nti_interfaces.IHighlight)
@interface.implementer(search_interfaces.IHighlightSearchHit)
class _HighlightSearchHit(_SearchHit):
	adapter_interface = search_interfaces.IHighlightContentResolver

@component.adapter(nti_interfaces.IRedaction)
@interface.implementer(search_interfaces.IRedactionSearchHit)
class _RedactionSearchHit(_SearchHit):

	adapter_interface = search_interfaces.IRedactionContentResolver

	RedactionExplanation = alias('replacementContent')
	ReplacementContent = alias('redactionExplanation')

	def set_hit_info(self, original, score):
		adapted = super(_RedactionSearchHit, self).set_hit_info(original, score)
		self.replacement_content = get_value(adapted, "replacementContent")
		self.redaction_explanation = get_value(adapted, "redactionExplanation")
		return adapted

	def get_replacement_content(self):
		return self.replacement_content

	def get_redaction_explanation(self):
		return self.redaction_explanation

@component.adapter(chat_interfaces.IMessageInfo)
@interface.implementer(search_interfaces.IMessageInfoSearchHit)
class _MessageInfoSearchHit(_SearchHit):
	adapter_interface = search_interfaces.IMessageInfoContentResolver

@component.adapter(for_interfaces.IPost)
@interface.implementer(search_interfaces.IPostSearchHit)
class _PostSearchHit(_SearchHit):

	adapter_interface = search_interfaces.IPostContentResolver

	Tags = alias('tags')
	Title = alias('title')

	def set_hit_info(self, original, score):
		adapted = super(_PostSearchHit, self).set_hit_info(original, score)
		self[TYPE] = POST
		self[ID] = get_value(adapted, "id")
		self.title = get_value(adapted, "title")
		self.tags = get_value(adapted, "tags" , ())
		return adapted

	def get_title(self):
		return self.title

	def get_tags(self):
		t = self.tags or ()
		return unicode(' '.join(t))

@component.adapter(search_interfaces.IWhooshBookContent)
@interface.implementer(search_interfaces.IWhooshBookSearchHit)
class _WhooshBookSearchHit(_BaseSearchHit):

	def __init__(self, hit):
		super(_WhooshBookSearchHit, self).__init__(hit, self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(_WhooshBookSearchHit, self).set_hit_info(hit, score)
		self[TYPE] = CONTENT
		self[NTIID] = hit.ntiid
		self[SNIPPET] = hit.content
		self[CONTAINER_ID] = hit.ntiid
		self[title_.capitalize()] = hit.title
		self[LAST_MODIFIED] = hit.last_modified
		self[TARGET_MIME_TYPE] = BOOK_CONTENT_MIME_TYPE

	@classmethod
	def get_oid(cls, hit):
		return unicode(hit.ntiid)

@component.adapter(search_interfaces.IWhooshVideoTranscriptContent)
@interface.implementer(search_interfaces.IWhooshVideoTranscriptSearchHit)
class _WhooshVideoTranscriptSearchHit(_BaseSearchHit):

	def __init__(self, hit):
		super(_WhooshVideoTranscriptSearchHit, self).__init__(hit, self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(_WhooshVideoTranscriptSearchHit, self).set_hit_info(hit, score)
		self[TYPE] = VIDEO_TRANSCRIPT
		self[TITLE] = hit.title
		self[NTIID] = hit.videoId
		self[SNIPPET] = hit.content
		self[VIDEO_ID] = hit.videoId
		self[CONTAINER_ID] = hit.containerId
		self[LAST_MODIFIED] = hit.last_modified
		self[END_MILLISECS] = hit.end_millisecs
		self[START_MILLISECS] = hit.start_millisecs
		self[TARGET_MIME_TYPE] = VIDEO_TRANSCRIPT_MIME_TYPE

	@classmethod
	def get_oid(cls, hit):
		result = (str(hit.docnum), u'-', hit.videoId)
		return unicode(''.join(result))

@component.adapter(search_interfaces.IWhooshNTICardContent)
@interface.implementer(search_interfaces.IWhooshNTICardSearchHit)
class _WhooshNTICardSearchHit(_BaseSearchHit):

	Title = alias('title')

	def __init__(self, hit):
		super(_WhooshNTICardSearchHit, self).__init__(hit, self.get_oid(hit))

	def set_hit_info(self, hit, score):
		super(_WhooshNTICardSearchHit, self).set_hit_info(hit, score)
		self[TYPE] = NTI_CARD
		self[HREF] = hit.href
		self[NTIID] = hit.ntiid
		self[TITLE] = hit.title
		self.title = hit.title
		self[SNIPPET] = hit.content
		self[CONTAINER_ID] = hit.containerId
		self[TARGET_NTIID] = hit.target_ntiid
		self[LAST_MODIFIED] = hit.last_modified
		self[TARGET_MIME_TYPE] = NTI_CARD_MIME_TYPE

	def get_title(self):
		return self.title or u''

	@classmethod
	def get_oid(cls, hit):
		return unicode(hit.ntiid)

