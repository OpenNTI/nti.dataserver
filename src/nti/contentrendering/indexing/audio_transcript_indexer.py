#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh audio transcript indexer.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.contentindexing.utils import videotimestamp_to_datetime

from nti.contentindexing.media.interfaces import IAudioTranscriptParser

from nti.contentindexing.whooshidx import AUDIO_TRANSCRIPT_IDXNAME_PREDIX
from nti.contentindexing.whooshidx.interfaces import IWhooshAudioTranscriptIndexer
from nti.contentindexing.whooshidx.interfaces import IWhooshAudioTranscriptSchemaCreator

from .media_transcript_indexer import _Media
from .media_transcript_indexer import _WhooshMediaTranscriptIndexer

class _Audio(_Media):
	pass

@interface.implementer(IWhooshAudioTranscriptIndexer)
class _WhooshAudioTranscriptIndexer(_WhooshMediaTranscriptIndexer):

	media_cls = _Audio
	media_prefix = AUDIO_TRANSCRIPT_IDXNAME_PREDIX
	media_mimeType = u'application/vnd.nextthought.ntiaudio'
	media_source_types = (u'application/vnd.nextthought.audiosource',)
	media_transcript_parser_interface = IAudioTranscriptParser
	media_transcript_schema_creator = IWhooshAudioTranscriptSchemaCreator

	def _add_document(self, writer, containerId, media_id, language, title, content,
					  keywords, last_modified, start_ts, end_ts):

		writer.add_document(containerId=containerId,
							audioId=media_id,
							language=language,
							title=title,
							content=content,
							quick=content,
							keywords=keywords,
							last_modified=last_modified,
							end_timestamp=videotimestamp_to_datetime(end_ts),
							start_timestamp=videotimestamp_to_datetime(start_ts))

_DefaultWhooshAudioTranscriptIndexer = _WhooshAudioTranscriptIndexer
