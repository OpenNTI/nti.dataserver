from __future__ import print_function, unicode_literals

import six
import uuid
import UserDict
import collections

import zope.intid
from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.externalization import interfaces as ext_interfaces

from nti.contentsearch.common import epoch_time
from nti.contentsearch._views_utils import get_ntiid_path
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._search_highlights import WORD_HIGHLIGHT

from nti.contentsearch.common import (	NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
										SNIPPET, HIT, ID, CONTENT, INTID, SCORE, OID)

from nti.contentsearch.common import ( last_modified_, content_, title_, ntiid_, intid_)

import logging
logger = logging.getLogger( __name__ )

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
class _BaseSearchHit(object, UserDict.DictMixin):
	def __init__( self, oid=None):
		self._data = {}
		self.oid = oid
		self._query = None
		
	def toExternalObject(self):
		return self._data
	
	def keys(self):
		return self._data.keys()
	
	def __getitem__(self, key):
		return self._data[key]
	
	def __setitem__(self, key, val):
		self._data[key] = val
		
	def __delitem__(self, key):
		self._data.pop(key)
		
	def get_query(self):
		return self._query
	
	def set_query(self, query):
		self._query = search_interfaces.ISearchQuery(query, None)
		
	query = property(get_query, set_query)
	
	def get_score(self):
		return self._data.get(SCORE, 1.0)
	
	def set_score(self, score=1.0):
		self._data[SCORE] = score or 1.0
		
	score = property(get_score, set_score)
	
	@property
	def last_modified(self):
		return self._data.get(LAST_MODIFIED, 0)
	
	def __repr__(self):
		return "<%s %r>" % (self.__class__.__name__, self._data)
	
class _SearchHit(_BaseSearchHit):
	def __init__( self, original, score=1.0 ):
		super(_SearchHit, self).__init__(get_hit_id(original))
		adapted = component.queryAdapter(original, search_interfaces.IContentResolver)
		self._data[CLASS] = HIT
		self._data[SCORE] = score
		self._data[TYPE] = original.__class__.__name__
		self._data[CREATOR] = adapted.get_creator() if adapted else u''
		self._data[NTIID] = adapted.get_ntiid() if adapted else u''
		self._data[SNIPPET] = adapted.get_content() if adapted else u''
		self._data[CONTAINER_ID] = adapted.get_containerId() if adapted else u''
		self._data[LAST_MODIFIED] = adapted.get_last_modified() if adapted else 0
		
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
		self._data[ID] = adapted.get_id() if adapted else u''
		
@component.adapter(search_interfaces.IWhooshBookContent)
class _WhooshBookSearchHit(_BaseSearchHit):
	
	def __init__( self, hit ):
		super(_WhooshBookSearchHit, self).__init__()
		self._data[CLASS] = HIT	
		self._data[TYPE] = CONTENT
		self._data[NTIID] = hit[ntiid_]
		self._data[SNIPPET] = hit[content_]
		self._data[CONTAINER_ID] = hit[ntiid_]
		self._data[title_.capitalize()] = hit[title_]
		self._data[LAST_MODIFIED] = epoch_time(hit[last_modified_])
		self.oid = ''.join((hit[ntiid_], u'-', unicode(hit[intid_])))
			
	@property
	def last_modified(self):
		return self._data.get(LAST_MODIFIED, 0)
	
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
	
	def get_score(self, item):
		if search_interfaces.IBaseHit.providedBy(item):
			result = item.score
		else:
			result = 1.0
		return result
	
	def compare(self, a, b):
		a_score = self.get_score(a)
		b_score = self.get_score(b)
		result = cmp(b_score, a_score)
		return result

@interface.implementer(search_interfaces.ISearchHitComparator)
class _RelevanceSearchHitComparator(_ScoreSearchHitComparator):

	def _path_common(self, x, y):
		count = 0
		_limit = min(len(x), len(y))
		for i in xrange(0, _limit):
			if x[i] == y[i]:
				count += 1
			else:
				break
		return count
	
	def get_ntiid_path(self, item):
		if isinstance(item, six.string_types):
			result = get_ntiid_path(item)
		elif search_interfaces.IBaseHit.providedBy(item):
			result = get_ntiid_path(item.query.location)
		else:
			result = ()
		return result
			
	def get_containerId(self, item):
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
		a_common = self._path_common(location_path, a_path)
		b_common = self._path_common(location_path, b_path)
		result = cmp(b_common, a_common)
		result = super(_RelevanceSearchHitComparator, self).compare(a, b) if result == 0 else result
		return result
