#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh content index classes.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.contentindexing.utils import video_date_to_millis

from nti.contentindexing.whooshidx.schemas import create_book_schema
from nti.contentindexing.whooshidx.schemas import create_nti_card_schema
from nti.contentindexing.whooshidx.schemas import create_audio_transcript_schema
from nti.contentindexing.whooshidx.schemas import create_video_transcript_schema

from nti.contentprocessing import rank_words

from nti.property.property import Lazy

from .interfaces import ISearchQuery

from . import common
from . import constants
from . import whoosh_query
from . import content_types
from . import search_results

from .constants import (content_, ntiid_, last_modified_, videoId_, creator_,
						containerId_, title_, end_timestamp_, start_timestamp_,
					 	href_, target_ntiid_)

class _SearchableContent(object):

	_schema = None

	prefix = u''
	type = None
	default_word_max_dist = 15

	def __init__(self, schema=None):
		if schema is not None:
			self._schema = schema

	@property
	def schema(self):
		return self._schema

	def _parse_query(self, query, **kwargs):
		query = ISearchQuery(query)
		parsed_query = whoosh_query.parse_query(query, self.schema)
		return query, parsed_query

	def search(self, searcher, query, store=None, *args, **kwargs):
		query, parsed_query = self._parse_query(query, **kwargs)
		store = search_results.get_or_create_search_results(query, store)
		results = self._execute_search(searcher, parsed_query, query, store=store)
		return results

	def suggest_and_search(self, searcher, query, store=None, *args, **kwargs):
		query = ISearchQuery(query)
		store = search_results.get_or_create_suggest_and_search_results(query, store)
		if ' ' in query.term or query.IsPrefixSearch or query.IsPhraseSearch:
			results = self.search(searcher, query, store)
		else:
			suggest_results = self.suggest(searcher, query)
			suggestions = list(suggest_results.Suggestions)
			if suggestions:
				suggestions = rank_words(query.term, suggestions)
				qo, parsed_query = self._parse_query(suggestions[0], **kwargs)
				results = self._execute_search(searcher, parsed_query, qo, store=store)
				results.add_suggestions(suggestions)
			else:
				results = self.search(searcher, query, store)
		return results

	def suggest(self, searcher, word, store=None, *args, **kwargs):
		query = ISearchQuery(word)
		prefix = query.prefix or len(query.term)
		maxdist = query.maxdist or self.default_word_max_dist
		results = search_results.get_or_create_suggest_results(query, store)
		records = searcher.suggest(content_, query.term, maxdist=maxdist, prefix=prefix)
		results.extend(records)
		return results

	def _execute_search(self, searcher, parsed_query, queryobject, store, docids=None):
		# execute search
		search_hits = searcher.search(parsed_query, limit=None)
		length = len(search_hits)
		if not length:
			return store

		objects = self.get_objects_from_whoosh_hits(search_hits, docids)
		store.extend(objects)
		return store

	def get_objects_from_whoosh_hits(self, search_hits, docids):
		raise NotImplementedError()

class Book(_SearchableContent):

	type = constants.content_
	prefix = constants.book_prefix

	@Lazy
	def schema(self):
		return self._schema or create_book_schema()

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
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
									 			 lastModified=last_modified)
				yield (data, score)

class VideoTranscript(_SearchableContent):

	type = constants.videotranscript_
	prefix = constants.vtrans_prefix

	@Lazy
	def schema(self):
		return self._schema or create_video_transcript_schema()

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		for hit in search_hits:
			docnum = hit.docnum
			if docids is None or docnum not in docids:
				if docids is not None:
					docids.add(docnum)
				score = hit.score or 1.0
				data = content_types.VideoTranscriptContent(
								score=score,
								docnum=docnum,
								title=hit[title_],
								content=hit[content_],
								videoId=hit[videoId_],
					 			containerId=hit[containerId_],
								lastModified=common.epoch_time(hit[last_modified_]),
					 			end_millisecs=video_date_to_millis(hit[end_timestamp_]),
					 			start_millisecs=video_date_to_millis(hit[start_timestamp_]))
				yield (data, score)

class AudioTranscript(_SearchableContent):

	type = constants.audiotranscript_
	prefix = constants.atrans_prefix

	@Lazy
	def schema(self):
		return self._schema or create_audio_transcript_schema()

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		for hit in search_hits:
			docnum = hit.docnum
			if docids is None or docnum not in docids:
				if docids is not None:
					docids.add(docnum)
				score = hit.score or 1.0
				data = content_types.AudioTranscriptContent(
								score=score,
								docnum=docnum,
								title=hit[title_],
								content=hit[content_],
								videoId=hit[videoId_],
					 			containerId=hit[containerId_],
								lastModified=common.epoch_time(hit[last_modified_]),
					 			end_millisecs=video_date_to_millis(hit[end_timestamp_]),
					 			start_millisecs=video_date_to_millis(hit[start_timestamp_]))
				yield (data, score)

class NTICard(_SearchableContent):

	type = constants.nticard_
	prefix = constants.nticard_prefix

	@Lazy
	def schema(self):
		return self._schema or create_nti_card_schema()

	def get_objects_from_whoosh_hits(self, search_hits, docids=None):
		for hit in search_hits:
			docnum = hit.docnum
			if docids is None or docnum not in docids:
				if docids is not None:
					docids.add(docnum)
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
										lastModified=last_modified,
								 		containerId=hit[containerId_],
								 		target_ntiid=hit[target_ntiid_])
				yield (data, score)
