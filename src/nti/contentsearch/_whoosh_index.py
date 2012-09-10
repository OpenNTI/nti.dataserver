from __future__ import print_function, unicode_literals

import inspect
from datetime import datetime

import zope.intid
from zope import interface
from zope import component

from whoosh import fields
from whoosh import highlight
from whoosh import analysis

from nti.contentsearch._search_query import QueryObject
from nti.contentsearch._whoosh_query import parse_query
from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._datastructures import CaseInsensitiveDict

from nti.contentsearch.common import normalize_type_name
from nti.contentsearch._search_results import empty_search_result
from nti.contentsearch._search_results import empty_suggest_result
from nti.contentsearch.common import (NTIID, LAST_MODIFIED, ITEMS, HIT_COUNT, SUGGESTIONS)
from nti.contentsearch._search_highlights import ( WORD_HIGHLIGHT, NGRAM_HIGHLIGHT, WHOOSH_HIGHLIGHT)

from nti.contentsearch.common import (	quick_, channel_, content_, keywords_, references_, 
										recipients_, sharedWith_, ntiid_, last_modified_,
										creator_, containerId_, replacementContent_,
										redactionExplanation_, intid_)
		
import logging
logger = logging.getLogger( __name__ )

_default_word_max_dist = 15

class _SearchableContent(object):
	
	__indexable__ = False
	
	@property
	def schema(self):
		return self.get_schema()
	
	def get_schema(self):
		return getattr(self, '_schema', None)
			
	def _parse_query(self, fieldname, query, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		parsed_query = parse_query(fieldname, qo, self.get_schema())
		return qo, parsed_query
	
	def get_search_highlight_type(self):
		return WORD_HIGHLIGHT
	
	def search(self, searcher, query, *args, **kwargs):
		qo, parsed_query = self._parse_query(content_, query, **kwargs)
		return self.execute_query_and_externalize(searcher, content_, parsed_query, qo,
												  self.get_search_highlight_type())
		
	def ngram_search(self, searcher, query, *args, **kwargs):
		qo, parsed_query = self._parse_query(quick_, query, **kwargs)
		return self.execute_query_and_externalize(searcher, quick_, parsed_query, qo, NGRAM_HIGHLIGHT)
	
	def suggest_and_search(self, searcher, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		if ' ' in qo.term:
			suggestions = []
			result = self.search(searcher, qo)
		else:
			result = self.suggest(searcher, qo)
			suggestions = result.get(ITEMS, None)
			if suggestions:
				qo.set_term(suggestions[0])
				result = self.search(searcher, qo)
			else:
				result = self.search(searcher, qo)

		result[SUGGESTIONS] = suggestions
		return result

	def suggest(self, searcher, word, *args, **kwargs):
		qo = QueryObject.create(word, **kwargs)
		limit = qo.limit
		prefix = qo.prefix or len(qo.term)
		maxdist = qo.maxdist or _default_word_max_dist
		result = empty_suggest_result(qo.term)
		records = searcher.suggest(content_, qo.term, maxdist=maxdist, prefix=prefix)
		records = records[:limit] if limit and limit > 0 else records
		result[ITEMS] = records
		result[HIT_COUNT] = len(records)
		return result

	def execute_query_and_externalize(self, searcher, search_field, parsed_query, queryobject, highlight_type=None):

		# execute search
		search_hits = searcher.search(parsed_query, limit=queryobject.limit)
		
		# set highlight type
		surround = queryobject.surround
		maxchars = queryobject.maxchars
		search_hits.formatter = highlight.UppercaseFormatter()
		search_hits.fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
		
		length = len(search_hits)
		query_term = queryobject.term
		result = empty_search_result(query_term)
		if not length:
			return result
		
		items = result[ITEMS]
		
		# return all source objects
		objects = self.get_objects_from_whoosh_hits(search_hits, search_field)
		
		# get all index hits
		hits = map(get_search_hit, objects, [query_term]*length, [highlight_type]*length)
		
		# get last modified
		lm = reduce(lambda x,y: max(x, y.get(LAST_MODIFIED,0)), hits, 0)
		for hit in hits:
			items[hit[NTIID]] = hit
			
		result[LAST_MODIFIED] = lm
		result[HIT_COUNT] = length
		return result

	def get_objects_from_whoosh_hits(self, search_hits, search_field):
		return search_hits

# content analyzer

def _content_analyzer():
	zutility = component.queryUtility(search_interfaces.IStopWords) 
	stopwords = zutility.stopwords() if zutility else analysis.STOP_WORDS
	analyzer = analysis.StandardAnalyzer(stoplist=stopwords) | analysis.NgramFilter(minsize=3, maxsize=10)
	return analyzer
	
# book content

def create_book_schema():
	"""
	Book index schema

	ntiid: Internal nextthought ID for the chapter/section
	title: chapter/section title
	last_modified: chapter/section last modification since the epoch
	keywords: chapter/section key words
	content: chapter/section text
	quick: chapter/section text ngrams
	related: ntiids of related sections
	ref: chapter reference
	"""
	
	schema = fields.Schema(	ntiid = fields.ID(stored=True, unique=False),
							title = fields.TEXT(stored=True, spelling=True),
				  			last_modified = fields.DATETIME(stored=True),
				  			keywords = fields.KEYWORD(stored=True), 
				 			quick = fields.NGRAM(maxsize=10, phrase=True),
				 			related = fields.KEYWORD(stored=True),
				 			content = fields.TEXT(stored=True, spelling=True, phrase=True, analyzer=_content_analyzer()))
	return schema

class Book(_SearchableContent):

	_schema = create_book_schema()
	
	def get_search_highlight_type(self):
		return WHOOSH_HIGHLIGHT
	
	def suggest(self, searcher, word, *args, **kwargs):
		result = super(Book, self).suggest(searcher, word, *args, **kwargs)
		records = result[ITEMS]
		if records:
			records = sorted(records, key=lambda x: len(x), reverse=True)
			result[ITEMS] = records
		return result
	
	def get_objects_from_whoosh_hits(self, search_hits, search_field):
		result = []
		for hit in search_hits:
			result.append(hit)
			hit.search_field = search_field
			interface.alsoProvides( hit, search_interfaces.IWhooshBookContent )
		return result

# ugd content getter 

def get_channel(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_channel()

def get_containerId(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_containerId()

def get_ntiid(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_ntiid()

def get_creator(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_creator()

def get_last_modified(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_last_modified()
	return datetime.fromtimestamp(result) if result is not None else None
	
def get_references(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_references()
	return unicode(','.join(result)) if result else None

def get_keywords(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	words = adapted.get_keywords()
	return unicode(','.join(words)) if words else None

def get_recipients(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_recipients()
	return unicode(','.join(result)) if result else None

def get_sharedWith(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_sharedWith()
	return unicode(','.join(result)) if result else None

def get_object_content(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_content()
	return result if result else None

def get_replacement_content(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_replacement_content()
	return result if result else None
	
def get_redaction_explanation(obj):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_redaction_explanation()
	return result if result else None

def get_uid(obj):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	uid = _ds_intid.getId(obj)
	return unicode(str(uid))
	
def get_object(uid):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	uid = int(uid)
	return _ds_intid.getObject(uid)

def is_ngram_search_supported():
	features = component.getUtility( search_interfaces.ISearchFeatures )
	return features.is_ngram_search_supported

def _create_user_indexable_content_schema():
	
	schema = fields.Schema(	intid = fields.ID(stored=True, unique=True),
							containerId = fields.ID(stored=False),
							creator = fields.ID(stored=False),
				  			last_modified = fields.DATETIME(stored=False),
				 			ntiid = fields.ID(stored=False))
	return schema
	
class UserIndexableContent(_SearchableContent):

	def get_search_highlight_type(self):
		return WORD_HIGHLIGHT
	
	def get_index_data(self, data, *args, **kwargs):
		"""
		return a dictonary with the info to be stored in the index
		"""
		result = {}
		result[intid_] = get_uid(data)
		result[ntiid_] = get_ntiid(data)
		result[creator_] = get_creator(data)
		result[containerId_] = get_containerId(data)
		result[last_modified_] = get_last_modified(data)
		return result

	def get_objects_from_whoosh_hits(self, search_hits, search_field):
		result = map(self._get_object, search_hits)
		return result
	
	def _get_object(self, hit):
		uid = hit[intid_]
		result = get_object(uid)
		return result
	
	def index_content(self, writer, data, auto_commit=True, **commit_args):
		d = self.get_index_data(data)
		try:
			writer.add_document(**d)
			if auto_commit:
				writer.commit(**commit_args)
			return True
		except Exception, e:
			writer.cancel()
			raise e
		return False

	def update_content(self, writer, data, auto_commit=True, **commit_args):
		d = self.get_index_data(data)
		try:
			writer.update_document(**d)
			if auto_commit:
				writer.commit(**commit_args)
			return True
		except Exception, e:
			writer.cancel()
			raise e
		return False
		
	def delete_content(self, writer, data, auto_commit=True, **commit_args):
		_dsid = get_uid(data)
		try:
			writer.delete_by_term(intid_, _dsid)
			if auto_commit:
				writer.commit(**commit_args)
			return True
		except Exception, e:
			writer.cancel()
			raise e
	
def _create_treadable_schema():
	schema = _create_user_indexable_content_schema()
	schema.add(keywords_, fields.KEYWORD(stored=False) )
	schema.add(sharedWith_, fields.TEXT(stored=False) )
	return schema

class TreadableIndexableContent(UserIndexableContent):
	
	_schema = _create_treadable_schema()
	
	def get_index_data(self, data, *args, **kwargs):
		result = super(TreadableIndexableContent, self).get_index_data(data,  *args, **kwargs)
		result[keywords_] = get_keywords(data)
		result[sharedWith_] = get_sharedWith(data)
		return result
	
# highlight
	
def create_highlight_schema():
	schema = _create_treadable_schema()
	schema.add(content_, fields.TEXT(stored=False, chars=True, spelling=True))
	schema.add(quick_, fields.NGRAM(maxsize=10, phrase=True))
	return schema

class Highlight(TreadableIndexableContent):

	__indexable__ = True
	_schema = create_highlight_schema()

	def get_index_data(self, data, *args, **kwargs):
		result = super(Highlight, self).get_index_data(data,  *args, **kwargs)
		result[content_] = get_object_content(data)
		result[quick_] = result[content_] if is_ngram_search_supported() else None
		return result
	
# redaction

def create_redaction_schema():
	schema = create_highlight_schema()
	schema.add(replacementContent_, fields.TEXT(stored=False, chars=True, spelling=True))
	schema.add(redactionExplanation_, fields.TEXT(stored=False, chars=True, spelling=True))
	return schema

class Redaction(Highlight):

	_schema = create_redaction_schema()

	def get_index_data(self, data, *args, **kwargs):
		result = super(Redaction, self).get_index_data(data,  *args, **kwargs)
		result[replacementContent_] = get_replacement_content(data)
		result[redactionExplanation_] = get_redaction_explanation(data)
		return result
	
# note

def create_note_schema():
	schema = create_highlight_schema()
	schema.add(references_, fields.KEYWORD(stored=False))
	return schema

class Note(Highlight):
	
	_schema = create_note_schema()
	
	def get_index_data(self, data, *args, **kwargs):
		result = super(Note, self).get_index_data(data,  *args, **kwargs)
		result[references_] = get_references(data)
		return result

# messageinfo

def create_messageinfo_schema():
	schema = create_note_schema()
	schema.add(channel_, fields.KEYWORD(stored=False))
	schema.add(recipients_, fields.TEXT(stored=False))
	return schema

class MessageInfo(Note):

	_schema = create_messageinfo_schema()

	def get_index_data(self, data, *args, **kwargs):
		result = super(MessageInfo, self).get_index_data(data,  *args, **kwargs)
		result[channel_] = get_channel(data)
		result[references_] = get_references(data)
		return result
	
# register indexable objects

_indexables = CaseInsensitiveDict()
for k,v in globals().items():
	if inspect.isclass(v) and getattr(v, '__indexable__', False):
		name = normalize_type_name(k)
		_indexables[name] = v()
		
def get_indexables():
	return _indexables.keys()

def get_indexable_object(type_name=None):
	name = normalize_type_name(type_name)
	result = _indexables.get(name, None)
	return result
