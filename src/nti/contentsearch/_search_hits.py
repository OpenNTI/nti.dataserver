# -*- coding: utf-8 -*-
"""
Defines adaptes for search hits and hit comparators.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
import uuid
import collections

from zope import component
from zope import interface

import repoze.lru

from nti.contentfragments import interfaces as frg_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as for_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.mimetype import mimetype

from ._views_utils import get_ntiid_path
from . import interfaces as search_interfaces

from .common import get_type_name
from .common import get_sort_order
from . import _discriminators as discriminators
from .constants import (title_)
from .constants import (NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE, SNIPPET, HIT, ID, CONTENT, SCORE, OID,
						POST, MIME_TYPE, VIDEO_ID, BOOK_CONTENT_MIME_TYPE, VIDEO_TRANSCRIPT, VIDEO_TRANSCRIPT_MIME_TYPE,
					 	START_TIMESTAMP, END_TIMESTAMP, NTI_CARD, NTI_CARD_MIME_TYPE, TITLE, HREF, TARGET_NTIID)

def get_hit_id(obj):
	if nti_interfaces.IModeledContent.providedBy(obj):
		result = unicode(discriminators.get_uid(obj))
	elif isinstance(obj, collections.Mapping):
		result = obj.get(OID, None)
	else:
		result = None
	return result or unicode(uuid.uuid4())

@interface.implementer(search_interfaces.ISearchHit)
class _BaseSearchHit(dict):

	def __init__(self, original, oid=None, score=1.0):
		self.oid = oid
		self._query = None
		self.set_hit_info(original, score)

	def set_hit_info(self, original, score):
		self[CLASS] = HIT
		self[SCORE] = score
		self[TYPE] = original.__class__.__name__
		self[MIME_TYPE] = mimetype.nti_mimetype_from_object(original, use_class=False) or u''

	def get_query(self):
		return self._query

	def set_query(self, query):
		self._query = search_interfaces.ISearchQuery(query, None)

	query = property(get_query, set_query)

	def get_score(self):
		return self.get(SCORE, 1.0)

	def set_score(self, score=1.0):
		self[SCORE] = score or 1.0

	score = property(get_score, set_score)

	@property
	def last_modified(self):
		return self.get(LAST_MODIFIED, 0)

class _SearchHit(_BaseSearchHit):

	adapter_interface = search_interfaces.IUserContentResolver

	def __init__(self, original, score=1.0):
		super(_SearchHit, self).__init__(original, get_hit_id(original), score)

	def set_hit_info(self, original, score):
		super(_SearchHit, self).set_hit_info(original, score)
		adapted = component.queryAdapter(original, self.adapter_interface)
		self[SNIPPET] = self.get_snippet(adapted)
		self[NTIID] = self.get_field(adapted, 'get_ntiid')
		self[CREATOR] = self.get_field(adapted, 'get_creator')
		self[CONTAINER_ID] = self.get_field(adapted, 'get_containerId')
		self[LAST_MODIFIED] = self.get_field(adapted, 'get_last_modified', 0)
		return adapted

	@classmethod
	def get_snippet(cls, adpated):
		text = cls.get_field(adpated, 'get_content') or u''
		text = component.getAdapter(text, frg_interfaces.IPlainTextContentFragment, name='text')
		return text

	@classmethod
	def get_field(cls, adapted, mnane, default=u''):
		m = getattr(adapted, mnane, None)
		return m() if m is not None else default

@component.adapter(nti_interfaces.INote)
@interface.implementer(search_interfaces.INoteSearchHit)
class _NoteSearchHit(_SearchHit):
	adapter_interface = search_interfaces.INoteContentResolver

	def set_hit_info(self, original, score):
		adapted = super(_NoteSearchHit, self).set_hit_info(original, score)
		self.title = self.get_field(adapted, "get_title")
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

	def set_hit_info(self, original, score):
		adapted = super(_RedactionSearchHit, self).set_hit_info(original, score)
		self.replacement_content = self.get_field(adapted, "get_replacement_content")
		self.redaction_explanation = self.get_field(adapted, "get_redaction_explanation")
		return adapted

	def get_replacement_content(self):
		return self.replacement_content or u''

	def get_redaction_explanation(self):
		return self.redaction_explanation or u''

@component.adapter(chat_interfaces.IMessageInfo)
@interface.implementer(search_interfaces.IMessageInfoSearchHit)
class _MessageInfoSearchHit(_SearchHit):

	adapter_interface = search_interfaces.IMessageInfoContentResolver

	def set_hit_info(self, original, score):
		adapted = super(_MessageInfoSearchHit, self).set_hit_info(original, score)
		self[ID] = self.get_field(adapted, "get_id")
		return adapted

@component.adapter(for_interfaces.IPost)
@interface.implementer(search_interfaces.IPostSearchHit)
class _PostSearchHit(_SearchHit):

	adapter_interface = search_interfaces.IPostContentResolver

	def set_hit_info(self, original, score):
		adapted = super(_PostSearchHit, self).set_hit_info(original, score)
		self[TYPE] = POST
		self[ID] = self.get_field(adapted, "get_id")
		self.tags = self.get_field(adapted, "get_tags")
		self.title = self.get_field(adapted, "get_title")
		return adapted

	def get_title(self):
		return self.title or u''

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
		self[MIME_TYPE] = BOOK_CONTENT_MIME_TYPE

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
		self[NTIID] = hit.videoId
		self[SNIPPET] = hit.content
		self[VIDEO_ID] = hit.videoId
		self[CONTAINER_ID] = hit.containerId
		self[LAST_MODIFIED] = hit.last_modified
		self[END_TIMESTAMP] = hit.end_timestamp
		self[START_TIMESTAMP] = hit.start_timestamp
		self[MIME_TYPE] = VIDEO_TRANSCRIPT_MIME_TYPE

	@classmethod
	def get_oid(cls, hit):
		tpl = (hit.containerId, u'-', hit.videoId)
		return unicode(''.join(tpl))

@component.adapter(search_interfaces.IWhooshNTICardContent)
@interface.implementer(search_interfaces.IWhooshNTICardSearchHit)
class _WhooshNTICardSearchHit(_BaseSearchHit):

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
		self[MIME_TYPE] = NTI_CARD_MIME_TYPE
		self[CONTAINER_ID] = hit.containerId
		self[TARGET_NTIID] = hit.target_ntiid
		self[LAST_MODIFIED] = hit.last_modified

	def get_title(self):
		return self.title or u''

	@classmethod
	def get_oid(cls, hit):
		return unicode(hit.ntiid)

def get_search_hit(obj, score=1.0, query=None):
	hit = search_interfaces.ISearchHit(obj, None) or _SearchHit(obj)
	hit.score = score
	hit.query = query
	return hit

# define search hit comparators

class _CallableComparator(object):

	def __call__(self, a, b):
		return self.compare(a, b)


@interface.implementer(search_interfaces.ISearchHitComparator)
class _ScoreSearchHitComparator(_CallableComparator):

	@classmethod
	def get_score(cls, item):
		result = item.score if search_interfaces.IBaseHit.providedBy(item) else 1.0
		return result

	@classmethod
	def compare_score(cls, a, b):
		a_score = cls.get_score(a)
		b_score = cls.get_score(b)
		result = cmp(b_score, a_score)
		return result

	@classmethod
	def get_type_name(cls, item):
		if search_interfaces.ISearchHit.providedBy(item):
			result = item.get(CLASS, u'')
		elif search_interfaces.IBaseHit.providedBy(item):
			result = get_type_name(item.obj)
		else:
			result = u''
		return result or u''

	@classmethod
	def compare(cls, a, b):
		return cls.compare_score(a, b)

@interface.implementer(search_interfaces.ISearchHitComparator)
class _LastModifiedSearchHitComparator(_CallableComparator):

	@classmethod
	def get_lm(cls, item):
		if search_interfaces.IIndexHit.providedBy(item):
			adapted = search_interfaces.ILastModifiedResolver(item.obj, None)
			result = adapted.get_last_modified() if adapted is not None else 0
		elif search_interfaces.ISearchHit.providedBy(item):
			result = item.get(LAST_MODIFIED, 0)
		else:
			result = 0
		return result

	@classmethod
	def compare_lm(cls, a, b):
		a_lm = cls.get_lm(a)
		b_lm = cls.get_lm(b)
		result = cmp(a_lm, b_lm)
		return result

	@classmethod
	def compare(cls, a, b):
		return cls.compare_lm(a, b)

@interface.implementer(search_interfaces.ISearchHitComparator)
class _TypeSearchHitComparator(_ScoreSearchHitComparator, _LastModifiedSearchHitComparator):

	@classmethod
	def compare_type(cls, a, b):
		a_order = get_sort_order(cls.get_type_name(a))
		b_order = get_sort_order(cls.get_type_name(b))
		result = cmp(a_order, b_order)
		return result

	@classmethod
	def compare(cls, a, b):
		result = cls.compare_type(a, b)
		if result == 0:
			result = cls.compare_lm(a, b)
		if result == 0:
			result = cls.compare_score(a, b)
		return result

@repoze.lru.lru_cache(300)
def path_intersection(x, y):
	result = []
	_limit = min(len(x), len(y))
	for i in xrange(0, _limit):
		if x[i] == y[i]:
			result.append(x[i])
		else:
			break
	return tuple(result)

@interface.implementer(search_interfaces.ISearchHitComparator)
class _RelevanceSearchHitComparator(_TypeSearchHitComparator):

	@classmethod
	def score_path(cls, reference, p):

		if not reference or not p:
			return 0

		ip = path_intersection(reference, p)
		if len(ip) == 0:
			result = 0  # no path intersection
		elif len(ip) == len(reference):
			if len(reference) == len(p):
				result = 10000  # give max priority to hits int the same location
			else:
				result = 9000  # hit is below
		elif len(ip) == len(p):  # p is n a subset of ref
			result = len(p) * 20
		else:  # common anscestors
			result = len(ip) * 20
			result -= len(p) - len(ip)

		return max(0, result)

	@classmethod
	def get_ntiid_path(cls, item):
		if isinstance(item, six.string_types):
			result = get_ntiid_path(item)
		elif search_interfaces.IBaseHit.providedBy(item):
			result = get_ntiid_path(item.query.location)
		else:
			result = ()
		return result

	@classmethod
	def get_containerId(cls, item):
		if search_interfaces.ISearchHit.providedBy(item):
			result = item.get(NTIID, None)
		elif search_interfaces.IIndexHit.providedBy(item):
			adapted = component.queryAdapter(item.obj, search_interfaces.IContainerIDResolver)
			result = adapted.get_containerId() if adapted else None
		else:
			result = None
		return result

	@classmethod
	def compare(cls, a, b):
		# compare location
		location_path = cls.get_ntiid_path(a)
		a_path = get_ntiid_path(cls.get_containerId(a))
		b_path = get_ntiid_path(cls.get_containerId(b))
		a_score_path = cls.score_path(location_path, a_path)
		b_score_path = cls.score_path(location_path, b_path)
		result = cmp(b_score_path, a_score_path)

		# compare types.
		if result == 0:
			result = cls.compare_type(a, b)

		# compare scores. Score comparation at the moment only make sense within the same types
		# when we go to a unified index this we no longer need to compare the types
		result = cls.compare_score(a, b) if result == 0 else result
		return result
