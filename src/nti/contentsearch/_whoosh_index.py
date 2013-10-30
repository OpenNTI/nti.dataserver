# -*- coding: utf-8 -*-
"""
Whoosh content index classes.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import inspect
from datetime import datetime

from nti.contentprocessing import rank_words

from nti.utils.maps import CaseInsensitiveDict

from . import common
from . import search_query
from . import content_types
from . import discriminators
from . import search_results
from ._whoosh_query import parse_query
from . import _whoosh_schemas as wschs

from .constants import (channel_, content_, keywords_, references_, sharedWith_,
						ntiid_, last_modified_, videoId_, creator_, containerId_,
						replacementContent_, redactionExplanation_, tags_, intid_,
					 	title_, quick_, end_timestamp_, start_timestamp_,
					 	href_, target_ntiid_)


# alias
video_date_to_millis = common.video_date_to_millis
empty_suggest_and_search_results = search_results.empty_suggest_and_search_results

class _SearchableContent(object):
	_schema = None
	default_word_max_dist = 15

	@property
	def schema(self):
		return self._schema

	def _parse_query(self, query, **kwargs):
		qo = search_query.QueryObject.create(query, **kwargs)
		parsed_query = parse_query(qo, self.schema, self.__class__.__name__.lower())
		return qo, parsed_query

	def search(self, searcher, query, *args, **kwargs):
		qo, parsed_query = self._parse_query(query, **kwargs)
		results = self._execute_search(searcher, parsed_query, qo)
		return results

	def suggest_and_search(self, searcher, query, *args, **kwargs):
		qo = search_query.QueryObject.create(query, **kwargs)
		if ' ' in qo.term or qo.is_prefix_search or qo.is_phrase_search:
			results = empty_suggest_and_search_results(qo)
			results += self.search(searcher, qo)
		else:
			result = self.suggest(searcher, qo)
			suggestions = list(result.suggestions)
			if suggestions:
				suggestions = rank_words(qo.term, suggestions)
				qo, parsed_query = self._parse_query(suggestions[0], **kwargs)

				results = \
					self._execute_search(
							searcher,
							parsed_query, qo,
							creator_method=empty_suggest_and_search_results)

				results.add_suggestions(suggestions)
			else:
				results = empty_suggest_and_search_results(qo)
				results += self.search(searcher, qo)

		return results

	def suggest(self, searcher, word, *args, **kwargs):
		qo = search_query.QueryObject.create(word, **kwargs)
		prefix = qo.prefix or len(qo.term)
		maxdist = qo.maxdist or self.default_word_max_dist
		results = search_results.empty_suggest_results(qo)
		records = searcher.suggest(content_, qo.term, maxdist=maxdist, prefix=prefix)
		results.add(records)
		return results

	def _execute_search(self, searcher, parsed_query, queryobject, docids=None,
						creator_method=None):
		creator_method = creator_method or search_results.empty_search_results
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


class Book(_SearchableContent):

	def __init__(self, schema=None):
		schema = schema or wschs.create_book_schema()
		self._schema = schema

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		result = []
		for hit in search_hits:
			docnum = hit.docnum
			if docids is None or docnum not in docids:
				if docids is not None:
					docids.add(docnum)

				score = hit.score or 1.0
				last_modified = common.epoch_time(hit[last_modified_])
				data = content_types.BookContent(docnum=docnum,
												 score=score,
												 ntiid=hit[ntiid_],
									 			 title=hit[title_],
									 			 content=hit[content_],
									 			 last_modified=last_modified)
				result.append(search_results.IndexHit(data, score))
		return result

class VideoTranscript(_SearchableContent):

	def __init__(self, schema=None):
		schema = schema or wschs.create_video_transcript_schema()
		self._schema = schema

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		result = []
		for hit in search_hits:
			docnum = hit.docnum
			score = hit.score or 1.0
			data = content_types.VideoTranscriptContent(
							score=score,
							docnum=docnum,
							title=hit[title_],
							content=hit[content_],
							videoId=hit[videoId_],
				 			containerId=hit[containerId_],
							last_modified=common.epoch_time(hit[last_modified_]),
				 			end_millisecs=video_date_to_millis(hit[end_timestamp_]),
				 			start_millisecs=video_date_to_millis(hit[start_timestamp_]))
			result.append(search_results.IndexHit(data, score))
		return result

class NTICard(_SearchableContent):

	def __init__(self, schema=None):
		schema = schema or wschs.create_nti_card_schema()
		self._schema = schema

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		result = []
		for hit in search_hits:
			docnum = hit.docnum
			score = hit.score or 1.0
			last_modified = common.epoch_time(hit[last_modified_])
			data = content_types.NTICardContent(
									score=score,
									docnum=docnum,
									href=hit[href_],
									ntiid=hit[ntiid_],
									title=hit[title_],
									creator=hit[creator_],
									description=hit[content_],
									last_modified=last_modified,
							 		containerId=hit[containerId_],
							 		target_ntiid=hit[target_ntiid_])
			result.append(search_results.IndexHit(data, score))
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
	uid = discriminators.get_uid(obj)
	return unicode(uid)

def get_object_from_ds(uid):
	result = discriminators.query_object(uid)
	if result is None:
		logger.debug('Could not find object with id %r' % uid)
	return result

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
				obj = self.get_object(uid)  # make sure we have access and cache it
				if obj is not None:
					result.append(search_results.IndexHit(uid, score))
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
		return self.unindex_content(writer, _dsid, auto_commit, **commit_args)

	def unindex_content(self, writer, uid, auto_commit=True, **commit_args):
		try:
			writer.delete_by_term(intid_, unicode(uid))
			if auto_commit:
				writer.commit(**commit_args)
			return True
		except Exception, e:
			writer.cancel()
			raise e

class ShareableIndexableContent(UserIndexableContent):

	_schema = wschs._create_shareable_schema()

	def get_index_data(self, data):
		result = super(ShareableIndexableContent, self).get_index_data(data)
		result[sharedWith_] = get_sharedWith(data)
		return result

class ThreadableIndexableContent(ShareableIndexableContent):

	_schema = wschs._create_threadable_schema()

	def get_index_data(self, data):
		result = super(ThreadableIndexableContent, self).get_index_data(data)
		result[keywords_] = get_keywords(data)
		return result

class Highlight(ThreadableIndexableContent):

	__indexable__ = True
	_schema = wschs.create_highlight_schema()

	def get_index_data(self, data):
		result = super(Highlight, self).get_index_data(data)
		obj_content = discriminators.get_object_content(data)
		result[quick_] = obj_content
		result[content_] = obj_content
		return result

class Redaction(Highlight):

	_schema = wschs.create_redaction_schema()

	def get_index_data(self, data):
		result = super(Redaction, self).get_index_data(data)
		result[replacementContent_] = discriminators.get_replacement_content(data)
		result[redactionExplanation_] = discriminators.get_redaction_explanation(data)
		return result

class Note(Highlight):

	_schema = wschs.create_note_schema()

	def get_index_data(self, data):
		result = super(Note, self).get_index_data(data)
		result[references_] = get_references(data)
		return result

class MessageInfo(Note):

	_schema = wschs.create_messageinfo_schema()

	def get_index_data(self, data):
		result = super(MessageInfo, self).get_index_data(data)
		result[references_] = get_references(data)
		result[channel_] = discriminators.get_channel(data)
		return result

class Post(ShareableIndexableContent):

	__indexable__ = True
	_schema = wschs.create_post_schema()

	def get_index_data(self, data):
		result = super(Post, self).get_index_data(data)
		result[tags_] = get_post_tags(data)
		result[title_] = discriminators.get_post_title(data)
		obj_content = discriminators.get_object_content(data)
		result[quick_] = obj_content
		result[content_] = obj_content
		return result

# register indexable objects

_indexables = CaseInsensitiveDict()
for k, v in globals().items():
	if inspect.isclass(v) and getattr(v, '__indexable__', False):
		name = common.normalize_type_name(k)
		_indexables[name] = v

def get_indexable_objects():
	result = {n:c() for n, c in _indexables.items()}
	return result

def get_indexable_object(type_name=None):
	name = common.normalize_type_name(type_name)
	clazz = _indexables.get(name, None)
	return clazz() if clazz else None
