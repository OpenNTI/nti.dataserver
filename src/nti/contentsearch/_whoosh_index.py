# -*- coding: utf-8 -*-
"""
Whoosh user search adapter.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import inspect
from datetime import datetime
from operator import methodcaller

import zope.intid
from zope import interface
from zope import component

from whoosh import fields
from whoosh import analysis

from nti.contentprocessing import rank_words
from nti.contentprocessing import default_ngram_maxsize
from nti.contentprocessing import default_ngram_minsize
from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentprocessing import default_word_tokenizer_pattern

from .common import epoch_time
from ._search_query import QueryObject
from ._whoosh_query import parse_query
from .common import normalize_type_name
from . import interfaces as search_interfaces
from . import _discriminators as discriminators
from ._datastructures import CaseInsensitiveDict
from ._search_results import empty_search_results
from ._search_results import empty_suggest_results
from ._search_results import empty_suggest_and_search_results

from .common import (channel_, content_, keywords_, references_,
					 recipients_, sharedWith_, ntiid_, last_modified_,
					 creator_, containerId_, replacementContent_, tags_,
					 redactionExplanation_, intid_, title_, quick_)
_default_word_max_dist = 15

class _SearchableContent(object):

	__indexable__ = False

	@property
	def schema(self):
		return self.get_schema()

	def get_schema(self):
		return getattr(self, '_schema', None)

	def _parse_query(self, query, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		parsed_query = parse_query(qo, self.schema, self.__class__.__name__.lower())
		return qo, parsed_query

	def search(self, searcher, query, *args, **kwargs):
		qo, parsed_query = self._parse_query(query, **kwargs)
		results = self._execute_search(searcher, parsed_query, qo)
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
				qo, parsed_query = self._parse_query(suggestions[0], **kwargs)

				results = self._execute_search(	searcher,
											 	parsed_query,
											 	qo,
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

	def _execute_search(self, searcher, parsed_query, queryobject, docids=None, creator_method=None):
		creator_method = creator_method or empty_search_results
		results = creator_method(queryobject)

		# execute search
		search_hits = searcher.search(parsed_query, limit=None)
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

def _ngram_minmax(lang='en'):
	ngc_util = component.queryUtility(cp_interfaces.INgramComputer, name=lang)
	minsize = ngc_util.minsize if ngc_util else default_ngram_minsize
	maxsize = ngc_util.maxsize if ngc_util else default_ngram_maxsize
	return (minsize, maxsize)

def create_ngram_field(lang='en'):
	minsize, maxsize = _ngram_minmax()
	expression = component.queryUtility(cp_interfaces.IWordTokenizerExpression, name=lang) or default_word_tokenizer_pattern
	tokenizer = analysis.RegexTokenizer(expression=expression)
	return fields.NGRAMWORDS(minsize=minsize, maxsize=maxsize, stored=False, tokenizer=tokenizer, at='start')

def create_content_analyzer(lang='en'):
	sw_util = component.queryUtility(search_interfaces.IStopWords, name=lang)
	expression = component.queryUtility(cp_interfaces.IWordTokenizerExpression, name=lang) or default_word_tokenizer_pattern
	stopwords = sw_util.stopwords() if sw_util else ()
	analyzer = 	analysis.StandardAnalyzer(expression=expression, stoplist=stopwords)
	return analyzer

def create_content_field(stored=True):
	return fields.TEXT(stored=stored, spelling=True, phrase=True, analyzer=create_content_analyzer())

# book content

@interface.implementer( search_interfaces.IWhooshBookSchemaCreator)
class _DefaultBookSchemaCreator(object):
	
	def create(self):
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
		schema = fields.Schema(	docid = fields.ID(stored=True, unique=False),
								ntiid = fields.ID(stored=True, unique=False),
								title = fields.TEXT(stored=True, spelling=True),
					  			last_modified = fields.DATETIME(stored=True),
					  			keywords = fields.KEYWORD(stored=True),
					 			quick = create_ngram_field(),
					 			related = fields.KEYWORD(stored=True),
					 			content = create_content_field(stored=True))
		return schema

def create_book_schema(name='en'):
	to_call = component.queryUtility(search_interfaces.IWhooshBookSchemaCreator, name=name) or _DefaultBookSchemaCreator()
	return to_call.create()

@interface.implementer(search_interfaces.IWhooshBookContent)
class _BookContent(dict):
	ntiid = property(methodcaller('get', ntiid_))
	title = property(methodcaller('get', title_))
	content = property(methodcaller('get', content_))
	last_modified = property(methodcaller('get', last_modified_))
	# whoosh specific
	intid = property(methodcaller('get', intid_))
	score = property(methodcaller('get','score', 1.0))
	# alias
	docnum = property(methodcaller('get', intid_))
	containerId = property(methodcaller('get', ntiid_))

class Book(_SearchableContent):

	@property
	def _schema(self):
		return create_book_schema()

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		result = []
		for hit in search_hits:
			docnum = hit.docnum
			if docids is None or docnum not in docids:
				if docids is not None:
					docids.add(docnum)

				score = hit.score or 1.0
				last_modified = epoch_time(hit[last_modified_])
				data = _BookContent(intid  = docnum,
									score  = score,
									ntiid  = hit[ntiid_],
						 			title  = hit[title_],
						 			content = hit[content_],
						 			last_modified = last_modified )
				result.append((data, score))
		return result

# ugd content getter

def get_last_modified(obj):
	result = discriminators.get_last_modified(obj)
	return datetime.fromtimestamp(result) if result is not None else None

def get_keywords(obj):
	words = discriminators.get_keywords(obj)
	return unicode(','.join(words)) if words else None

def get_sharedWith(obj):
	result = discriminators.get_sharedWith(obj)
	return unicode(','.join(result)) if result else None

def get_references(obj):
	result = discriminators.get_references(obj)
	return unicode(','.join(result)) if result else None

def get_recipients(obj):
	result = discriminators.get_recipients(obj)
	return unicode(','.join(result)) if result else None

def get_post_tags(obj):
	tags = discriminators.get_post_tags(obj)
	return unicode(','.join(tags)) if tags else None

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

def _create_user_indexable_content_schema():

	schema = fields.Schema(	intid = fields.ID(stored=True, unique=True),
							containerId = fields.ID(stored=False),
							creator = fields.ID(stored=False),
				  			last_modified = fields.DATETIME(stored=False),
				 			ntiid = fields.ID(stored=False))
	return schema

class UserIndexableContent(_SearchableContent):

	def get_index_data(self, data):
		"""
		return a dictonary with the info to be stored in the index
		"""
		result = {}
		result[intid_] = get_uid(data)
		result[ntiid_] = discriminators.get_ntiid(data)
		result[last_modified_] = get_last_modified(data)
		result[creator_] = discriminators.get_creator(data)
		result[containerId_] = discriminators.get_containerId(data)
		return result

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		result = []
		for hit in search_hits:
			uid = int(hit[intid_])
			if docids is None or uid not in docids:
				if docids is not None:
					docids.add(uid)
				score = hit.score or 1.0
				obj = self.get_object(uid)
				result.append((obj, score))
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

def _create_shareable_schema():
	schema = _create_user_indexable_content_schema()
	schema.add(sharedWith_, fields.TEXT(stored=False) )
	return schema

class ShareableIndexableContent(UserIndexableContent):

	_schema = _create_shareable_schema()

	def get_index_data(self, data):
		result = super(ShareableIndexableContent, self).get_index_data(data)
		result[sharedWith_] = get_sharedWith(data)
		return result
	
def _create_threadable_schema():
	schema = _create_shareable_schema()
	schema.add(keywords_, fields.KEYWORD(stored=False) )
	return schema

class ThreadableIndexableContent(ShareableIndexableContent):

	_schema = _create_threadable_schema()

	def get_index_data(self, data):
		result = super(ThreadableIndexableContent, self).get_index_data(data)
		result[keywords_] = get_keywords(data)
		return result

# highlight

def create_highlight_schema():
	schema = _create_threadable_schema()
	schema.add(content_, create_content_field(stored=False))
	schema.add(quick_, create_ngram_field())
	return schema

class Highlight(ThreadableIndexableContent):

	__indexable__ = True
	_schema = create_highlight_schema()

	def get_index_data(self, data):
		result = super(Highlight, self).get_index_data(data)
		content = discriminators.get_object_content(data)
		result[quick_] = content
		result[content_] = content
		return result

# redaction

def create_redaction_schema():
	schema = create_highlight_schema()
	schema.add(replacementContent_, create_content_field(stored=False))
	schema.add(redactionExplanation_, create_content_field(stored=False))
	return schema

class Redaction(Highlight):

	_schema = create_redaction_schema()

	def get_index_data(self, data):
		result = super(Redaction, self).get_index_data(data)
		result[replacementContent_] = discriminators.get_replacement_content(data)
		result[redactionExplanation_] = discriminators.get_redaction_explanation(data)
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
		result[references_] = get_references(data)
		result[channel_] = discriminators.get_channel(data)
		return result

# post

def create_post_schema():
	schema = _create_shareable_schema()
	schema.add(content_, create_content_field(stored=False))
	schema.add(quick_, create_ngram_field())
	schema.add(title_, fields.TEXT(stored=False))
	schema.add(tags_, fields.KEYWORD(stored=False))
	return schema

class Post(ShareableIndexableContent):

	__indexable__ = True
	_schema = create_post_schema()

	def get_index_data(self, data):
		result = super(Post, self).get_index_data(data)
		result[tags_] = get_post_tags(data)
		result[title_] = discriminators.get_post_title(data)
		content = discriminators.get_object_content(data)
		result[quick_] = content
		result[content_] = content
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
