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

from nti.contentsearch.constants import atrans_prefix
from nti.contentsearch.common import videotimestamp_to_datetime
from nti.contentsearch.interfaces import IWhooshAudioTranscriptSchemaCreator

from ..media.interfaces import IAudioTranscriptParser

from .interfaces import IWhooshAudioTranscriptIndexer

from .media_transcript_indexer import _Media
from .media_transcript_indexer import _WhooshMediaTranscriptIndexer

class _Audio(_Media):
	pass

@interface.implementer(IWhooshAudioTranscriptIndexer)
class _WhooshAudioTranscriptIndexer(_WhooshMediaTranscriptIndexer):

	media_cls = _Audio
	media_prefix = atrans_prefix
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
