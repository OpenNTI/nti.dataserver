from __future__ import print_function, unicode_literals

import inspect
from datetime import datetime

import zope.intid
from zope import interface
from zope import component

from whoosh import fields
from whoosh import analysis
from whoosh import highlight
from whoosh.util import rcompile

from nti.contentsearch._search_query import QueryObject
from nti.contentsearch._whoosh_query import parse_query
from nti.contentsearch._content_utils import rank_words
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import default_ngram_maxsize
from nti.contentsearch.common import default_ngram_minsize
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._datastructures import CaseInsensitiveDict
from nti.contentsearch._search_results import empty_search_results
from nti.contentsearch._search_results import empty_suggest_results
from nti.contentsearch.common import default_word_tokenizer_expression
from nti.contentsearch._search_results import empty_suggest_and_search_results
from nti.contentsearch._search_highlights import ( WORD_HIGHLIGHT, WHOOSH_HIGHLIGHT)

from nti.contentsearch.common import (	channel_, content_, keywords_, references_, 
										recipients_, sharedWith_, ntiid_, last_modified_,
										creator_, containerId_, replacementContent_,
										redactionExplanation_, intid_, title_, quick_)
		
import logging
logger = logging.getLogger( __name__ )

_default_word_max_dist = 15
_default_expression = rcompile(default_word_tokenizer_expression)

class _SearchableContent(object):
	
	__indexable__ = False
	
	@property
	def schema(self):
		return self.get_schema()
	
	def get_schema(self):
		return getattr(self, '_schema', None)
			
	def _get_search_fields(self, queryobject):
		if queryobject.is_phrase_search or queryobject.is_prefix_search:
			result = (content_,)
		else:
			result = (quick_, content_)
		return result
	
	def _parse_query(self, query, **kwargs):
		parsed_query = None
		qo = QueryObject.create(query, **kwargs)
		fieldnames = self._get_search_fields(qo)
		for fieldname in fieldnames:
			pq = parse_query(fieldname, qo, self.get_schema())
			parsed_query = pq | parsed_query if parsed_query else pq
		return qo, parsed_query
	
	def get_search_highlight_type(self):
		return WORD_HIGHLIGHT
	
	def search(self, searcher, query, *args, **kwargs):
		qo, parsed_query = self._parse_query(query, **kwargs)
		results = self._execute_search(searcher, parsed_query, qo, highlight_type=self.get_search_highlight_type())
		return results
		
	def suggest_and_search(self, searcher, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		if ' ' in qo.term or qo.is_prefix_search or qo.is_phrase_search:
			results = empty_suggest_and_search_results(qo)
			results += self.search(searcher, qo)
		else:
			result = self.suggest(searcher, qo)
			suggestions = list(result.suggestions)
			if suggestions:
				suggestions = rank_words(qo.term, suggestions)
				qo.set_term(suggestions[0])
				parsed_query = parse_query(content_, qo, self.get_schema())
				
				results = self._execute_search(	searcher,
											 	parsed_query,
											 	qo,
											 	highlight_type=self.get_search_highlight_type(), 
											 	creator_method=empty_suggest_and_search_results)
				results.add_suggestions(suggestions)
			else:
				results = empty_suggest_and_search_results(qo)
				results += self.search(searcher, qo)

		return results

	def suggest(self, searcher, word, *args, **kwargs):
		qo = QueryObject.create(word, **kwargs)
		prefix = qo.prefix or len(qo.term)
		maxdist = qo.maxdist or _default_word_max_dist
		results = empty_suggest_results(qo)
		records = searcher.suggest(content_, qo.term, maxdist=maxdist, prefix=prefix)
		results.add(records)
		return results
	
	def _execute_search(self, searcher, parsed_query, queryobject, docids=None, highlight_type=None, creator_method=None):
		creator_method = creator_method or empty_search_results
		results = creator_method(queryobject)
		results.highlight_type = highlight_type
		
		# execute search
		search_hits = searcher.search(parsed_query, limit=None)
		
		# set highlight type
		surround = queryobject.surround
		maxchars = queryobject.maxchars
		search_hits.formatter = highlight.NullFormatter() #highlight.UppercaseFormatter()
		search_hits.fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
		
		length = len(search_hits)
		if not length:
			return results
		
		# return all source objects
		objects = self.get_objects_from_whoosh_hits(search_hits, docids)
		results.add(objects)
		
		return results

	def get_objects_from_whoosh_hits(self, search_hits, docids):
		raise NotImplementedError()

# content analyzer

def ngram_minmax():
	ngc_util = component.queryUtility(search_interfaces.INgramComputer) 
	minsize = ngc_util.minsize if ngc_util else default_ngram_minsize
	maxsize = ngc_util.maxsize if ngc_util else default_ngram_maxsize
	return (minsize, maxsize)

def content_analyzer():
	sw_util = component.queryUtility(search_interfaces.IStopWords) 
	stopwords = sw_util.stopwords() if sw_util else ()
	analyzer = 	analysis.StandardAnalyzer(expression=_default_expression, stoplist=stopwords)
	return analyzer
	
# book content

def create_book_schema():
	"""
	Book index schema

	docid: Unique id
	ntiid: Internal nextthought ID for the chapter/section
	title: chapter/section title
	last_modified: chapter/section last modification since the epoch
	keywords: chapter/section key words
	content: chapter/section text
	quick: chapter/section text ngrams
	related: ntiids of related sections
	ref: chapter reference
	"""
	minsize, maxsize = ngram_minmax()
	schema = fields.Schema(	docid = fields.ID(stored=True, unique=True),
							ntiid = fields.ID(stored=True, unique=False),
							title = fields.TEXT(stored=True, spelling=True),
				  			last_modified = fields.DATETIME(stored=True),
				  			keywords = fields.KEYWORD(stored=True), 
				 			quick = fields.NGRAM(minsize=minsize, maxsize=maxsize, phrase=True, stored=False),
				 			related = fields.KEYWORD(stored=True),
				 			content = fields.TEXT(stored=True, spelling=True, phrase=True, analyzer=content_analyzer()))
	return schema

#TODO: do an adapter
@interface.implementer(search_interfaces.IWhooshBookContent)
class _BookHit(dict):
	pass

class Book(_SearchableContent):

	_schema = create_book_schema()
	
	def get_search_highlight_type(self):
		return WHOOSH_HIGHLIGHT
	
	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		result = []
		for hit in search_hits:
			docnum = hit.docnum
			if docids is None or docnum not in docids:
				if docids is not None:
					docids.add(docnum)
					
				data = _BookHit(intid_ = docnum,
								ntiid  = hit[ntiid_], 
						 		title  = hit[title_],
						 		content = hit[content_],
						 		last_modified = hit[last_modified_] )
				result.append(data)
		return result

	def _set_whoosh_highlight(self, data, hit, search_field):
		try:
			whoosh_highlight = hit.highlights(search_field)
			if whoosh_highlight:
				data['whoosh_highlight'] = whoosh_highlight
		except:
			pass
			
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
	
def get_object_from_ds(uid):
	uid = int(uid)
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	result = _ds_intid.queryObject(uid, None)
	if result is None:
		logger.debug('Could not find object with id %r' % uid)
	return result
		
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
	
	def get_index_data(self, data):
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

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		result = []
		for hit in search_hits:
			uid = int(hit[intid_])
			if docids is None or uid not in docids:
				if docids is not None:
					docids.add(uid)
				obj = self.get_object(uid)
				result.append(obj)
		return result
	
	def get_object(self, uid):
		result = get_object_from_ds(uid)
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
	
	def get_index_data(self, data):
		result = super(TreadableIndexableContent, self).get_index_data(data)
		result[keywords_] = get_keywords(data)
		result[sharedWith_] = get_sharedWith(data)
		return result
	
# highlight

def create_highlight_schema():	
	minsize, maxsize = ngram_minmax() 			
	schema = _create_treadable_schema()
	schema.add(content_, fields.TEXT(stored=False, spelling=True, phrase=True, analyzer=content_analyzer()))
	schema.add(quick_, fields.NGRAM(minsize=minsize, maxsize=maxsize, phrase=True, stored=False))
	return schema

class Highlight(TreadableIndexableContent):

	__indexable__ = True
	_schema = create_highlight_schema()

	def get_index_data(self, data):
		result = super(Highlight, self).get_index_data(data)
		content_to_idx = get_object_content(data)
		result[content_] = content_to_idx
		result[quick_] = content_to_idx
		return result
	
# redaction

def create_redaction_schema():
	schema = create_highlight_schema()
	schema.add(replacementContent_, fields.TEXT(stored=False, chars=True, spelling=True))
	schema.add(redactionExplanation_, fields.TEXT(stored=False, chars=True, spelling=True))
	return schema

class Redaction(Highlight):

	_schema = create_redaction_schema()

	def get_index_data(self, data):
		result = super(Redaction, self).get_index_data(data)
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
	
	def get_index_data(self, data):
		result = super(Note, self).get_index_data(data)
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

	def get_index_data(self, data):
		result = super(MessageInfo, self).get_index_data(data)
		result[channel_] = get_channel(data)
		result[references_] = get_references(data)
		return result
	
# register indexable objects

_indexables = CaseInsensitiveDict()
for k,v in globals().items():
	if inspect.isclass(v) and getattr(v, '__indexable__', False):
		name = normalize_type_name(k)
		_indexables[name] = v
		
def get_indexables():
	return _indexables.keys()

def get_indexable_object(type_name=None):
	name = normalize_type_name(type_name)
	clazz = _indexables.get(name, None)
	return clazz() if clazz else None
