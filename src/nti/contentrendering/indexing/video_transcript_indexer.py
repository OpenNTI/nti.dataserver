#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh video transcript indexer.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.contentindexing.utils import videotimestamp_to_datetime

from nti.contentindexing.media.interfaces import IVideoTranscriptParser

from nti.contentindexing.whooshidx import VIDEO_TRANSCRIPT_IDXNAME_PREDIX
from nti.contentindexing.whooshidx.interfaces import IWhooshVideoTranscriptIndexer
from nti.contentindexing.whooshidx.interfaces import IWhooshVideoTranscriptSchemaCreator

from .media_transcript_indexer import _Media
from .media_transcript_indexer import WhooshMediaTranscriptIndexer

class _Video(_Media):

	@property
	def video_path(self):
		return self.path

	@property
	def video_ntiid(self):
		return self.ntiid

@interface.implementer(IWhooshVideoTranscriptIndexer)
class WhooshVideoTranscriptIndexer(WhooshMediaTranscriptIndexer):

	media_cls = _Video
	media_prefix = VIDEO_TRANSCRIPT_IDXNAME_PREDIX
	media_mimeType = u'application/vnd.nextthought.ntivideo'
	media_source_types = (u'application/vnd.nextthought.videosource',)
	media_transcript_parser_interface = IVideoTranscriptParser
	media_transcript_schema_creator = IWhooshVideoTranscriptSchemaCreator

	def _add_document(self, writer, containerId, media_id, language, title, content,
					  keywords, last_modified, start_ts, end_ts):

		writer.add_document(containerId=containerId,
							videoId=media_id,
							language=language,
							title=title,
							content=content,
							quick=content,
							keywords=keywords,
							last_modified=last_modified,
							end_timestamp=videotimestamp_to_datetime(end_ts),
							start_timestamp=videotimestamp_to_datetime(start_ts))

_DefaultWhooshVideoTranscriptIndexer = _WhooshVideoTranscriptIndexer = WhooshVideoTranscriptIndexer
