from __future__ import print_function, unicode_literals

import six
import uuid
import collections

import zope.intid
from zope import component
from zope import interface

import repoze.lru

from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.externalization import interfaces as ext_interfaces

from nti.contentsearch._views_utils import get_ntiid_path
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._search_highlights import WORD_HIGHLIGHT

from nti.contentsearch.common import (	NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
										SNIPPET, HIT, ID, CONTENT, INTID, SCORE, OID)

from nti.contentsearch.common import ( last_modified_, content_, title_, ntiid_, intid_)

hit_search_external_fields  = (	CLASS, CREATOR, TYPE, LAST_MODIFIED, NTIID, CONTAINER_ID, SNIPPET, ID, INTID)

def get_uid(obj):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	uid = _ds_intid.getId(obj)
	return uid

def get_hit_id(obj):
	if nti_interfaces.IModeledContent.providedBy(obj):
		result = unicode(get_uid(obj))
	elif isinstance(obj, collections.Mapping):
		result = obj.get(OID, None)
	else:
		result = None
	return result or unicode(uuid.uuid4())

@interface.implementer(search_interfaces.ISearchHit)
class _BaseSearchHit(dict):
	def __init__( self, oid=None):
		self.oid = oid
		self[CLASS] = HIT
		self._query = None
				
	def toExternalObject(self):
		return self
		
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
	def __init__( self, original, score=1.0 ):
		super(_SearchHit, self).__init__(get_hit_id(original))
		adapted = component.queryAdapter(original, search_interfaces.IContentResolver)
		self[SCORE] = score
		self[TYPE] = original.__class__.__name__
		self[CREATOR] = adapted.get_creator() if adapted else u''
		self[NTIID] = adapted.get_ntiid() if adapted else u''
		self[SNIPPET] = adapted.get_content() if adapted else u''
		self[CONTAINER_ID] = adapted.get_containerId() if adapted else u''
		self[LAST_MODIFIED] = adapted.get_last_modified() if adapted else 0
		
@component.adapter(nti_interfaces.IHighlight)
class _HighlightSearchHit(_SearchHit):
	pass
	
@component.adapter(nti_interfaces.IRedaction)
class _RedactionSearchHit(_SearchHit):
	pass
		
@component.adapter(nti_interfaces.INote)
class _NoteSearchHit(_SearchHit):
	pass
	
@component.adapter(chat_interfaces.IMessageInfo)
class _MessageInfoSearchHit(_SearchHit):
	def __init__( self, original, score=1.0 ):
		super(_MessageInfoSearchHit, self).__init__(original, score)
		adapted = component.queryAdapter(original, search_interfaces.IContentResolver)
		self[ID] = adapted.get_id() if adapted else u''
		
@component.adapter(search_interfaces.IWhooshBookContent)
class _WhooshBookSearchHit(_BaseSearchHit):
	
	def __init__( self, hit ):
		super(_WhooshBookSearchHit, self).__init__()
		self[TYPE] = CONTENT
		self[NTIID] = hit[ntiid_]
		self[SNIPPET] = hit[content_]
		self[CONTAINER_ID] = hit[ntiid_]
		self[title_.capitalize()] = hit[title_]
		self[LAST_MODIFIED] = hit[last_modified_]
		self.oid = ''.join((hit[ntiid_], u'-', unicode(hit[intid_])))

def _provide_highlight_snippet(hit, query=None, highlight_type=WORD_HIGHLIGHT):
	if hit is not None:
		hit.query = query
		if highlight_type == WORD_HIGHLIGHT:
			interface.alsoProvides( hit, search_interfaces.IWordSnippetHighlight )
		else:
			interface.alsoProvides( hit, search_interfaces.INoSnippetHighlight )
	return hit

def get_search_hit(obj, score=1.0, query=None, highlight_type=WORD_HIGHLIGHT):
	hit = component.queryAdapter( obj, ext_interfaces.IExternalObject, default=None, name='search-hit')
	hit = hit or _SearchHit(obj)
	hit.score = score
	hit.query = query
	hit = _provide_highlight_snippet(hit, query, highlight_type)
	return hit

@interface.implementer(search_interfaces.ISearchHitComparator)
class _ScoreSearchHitComparator(object):
	
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
	
	def compare(self, a, b):
		return self.compare_score(a, b)

@interface.implementer(search_interfaces.ISearchHitComparator)
class _LastModifiedSearchHitComparator(object):
	
	@classmethod
	def get_lm(cls, item):
		obj = item.obj if search_interfaces.IBaseHit.providedBy(item) else item
		rsr = search_interfaces.ILastModifiedResolver(obj, None)
		result = rsr.get_last_modified() if rsr is not None else 0
		return result
	
	@classmethod
	def compare_lm(cls, a, b):
		a_lm = cls.get_lm(a)
		b_lm = cls.get_lm(b)
		result = cmp(a_lm, b_lm)
		return result
	
	def compare(self, a, b):
		return self.compare_lm(a, b)

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
class _RelevanceSearchHitComparator(_ScoreSearchHitComparator):

	@classmethod
	def score_path(cls, reference, p):
		
		if not reference or not p:
			return 0
		
		ip = path_intersection(reference, p)
		if len(ip) == 0:
			result = 0 # no path intersection
		elif len(ip) == len(reference):
			if len(reference) == len(p):
				result = 10000  # give max priority to hits int the same location
			else:
				result = 9000 # hit is below
		elif len(ip) == len(p): # p is n a subset of ref
			result = len(p) * 20
		else: # common anscestors
			result = len(ip) * 20
			result -= len(p) - len(ip)
			
		return max(0,result) 
	
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
	
	def compare(self, a, b):
		location_path = self.get_ntiid_path(a)
		a_path = get_ntiid_path(self.get_containerId(a))
		b_path = get_ntiid_path(self.get_containerId(b))
		a_score = self.score_path(location_path, a_path)
		b_score = self.score_path(location_path, b_path)
		result = cmp(b_score, a_score)
		result = super(_RelevanceSearchHitComparator, self).compare(a, b) if result == 0 else result
		return result
