# -*- coding: utf-8 -*-
"""
Whoosh content index classes.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.contentprocessing import rank_words

from . import common
from . import search_query
from . import content_types
from . import search_results
from ._whoosh_query import parse_query
from . import _whoosh_schemas as wschs

from .constants import (content_, ntiid_, last_modified_, videoId_, creator_,
						containerId_, title_, end_timestamp_, start_timestamp_,
					 	href_, target_ntiid_)


# alias BWC

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

