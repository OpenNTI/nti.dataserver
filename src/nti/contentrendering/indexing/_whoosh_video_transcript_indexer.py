# -*- coding: utf-8 -*-
"""
Whoosh video transcript indexer.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import time
from datetime import datetime

from zope import component
from zope import interface

from nti.contentprocessing import get_content_translation_table

from nti.contentsearch import vtrans_prefix
from nti.contentsearch import videotimestamp_to_datetime
from nti.contentsearch import interfaces as search_interfaces

from . import _node_utils as node_utils
from . import _content_utils as content_utils
from . import interfaces as cridxr_interfaces
from ._common_indexer import _BasicWhooshIndexer
from ..media import interfaces as media_interfaces

@interface.implementer(cridxr_interfaces.IWhooshVideoTranscriptIndexer)
class _WhooshVideoTranscriptIndexer(_BasicWhooshIndexer):

	def get_schema(self, name='en'):
		creator = component.getUtility(search_interfaces.IWhooshVideoTranscriptSchemaCreator, name=name)
		return creator.create()

	@classmethod
	def _get_video_transcript_parser_names(cls):
		utils = component.getUtilitiesFor(media_interfaces.IVideoTranscriptParser)
		result = [x for x, _ in utils]
		return result

	def _parse_externalvideo_node(self, node):
		result = None
		for obj in node.iterchildren():
			if obj.tag != 'object': continue
			type_ = node_utils.get_attribute(obj, 'type')
			itemprop = node_utils.get_attribute(obj, 'itemprop')
			if itemprop == 'nti-slide-video' and type_ == 'application/vnd.nextthought.slidevideo':
				result = {}
				for p in obj.iterchildren():
					if p.tag != 'param': continue
					name = node_utils.get_attribute(p, 'name')
					value = node_utils.get_attribute(p, 'value')
					if name and value:
						result[name] = value
				break
		return result

	def _find_video_transcript(self, base_location, bases, parser_names):
		for location in ('.', '../Transcripts', './Transcripts'):
			path = os.path.join(base_location, location)
			if not os.path.exists(path):
				continue
			for pn in parser_names:
				ext = '.' + pn
				for basename in bases:
					fname = basename + ext
					video_path = os.path.join(path, fname)
					if os.path.exists(video_path):
						return pn, video_path
		return None

	def _get_externalvideo_info(self, topic, node):
		type_ = node_utils.get_attribute(node, 'type')
		if type_ == u'application/vnd.nextthought.slidevideo':
			result = {}
			for p in node.iterchildren():
				if p.tag != 'param': continue
				name = node_utils.get_attribute(p, 'name')
				value = node_utils.get_attribute(p, 'value')
				if name and value:
					result[name] = value

			video_id = result.get('id')
			video_type = result.get('type')
			video_ntiid = result.get('ntiid')
			parser_names = self._get_video_transcript_parser_names()
			content_path = os.path.dirname(topic.location)

			# collect video-base names
			bases = {video_ntiid}
			if video_type == 'youtube':
				bases.add(video_id)
			bases.discard(None)
			
			vid_tupl = self._find_video_transcript(content_path, bases, parser_names)
			if vid_tupl:
				parser_name, video_path = vid_tupl
				return (parser_name, video_ntiid, video_path)

		return None

	def index_transcript_entry(self, writer, containerId, video_id, entry, language=u'en'):
		try:
			content = entry.transcript
			table = get_content_translation_table(language)
			last_modified = datetime.fromtimestamp(time.time())
			content = unicode(content_utils.sanitize_content(content, table=table))
			writer.add_document(containerId=containerId,
								videoId=video_id,
								content=content,
								quick=content,
								last_modified=last_modified,
								end_timestamp=videotimestamp_to_datetime(entry.end_timestamp),
								start_timestamp=videotimestamp_to_datetime(entry.start_timestamp))
		except Exception:
			writer.cancel()
			raise

	def get_index_name(self, book, indexname=None):
		indexname = super(_WhooshVideoTranscriptIndexer, self).get_index_name(book, indexname)
		indexname = vtrans_prefix + indexname
		return indexname

	def process_topic(self, idxspec, topic, writer, language='en'):
		count = 0
		containerId = unicode(topic.ntiid)
		for n in topic.dom(b'object'):
			info = self._get_externalvideo_info(topic, n)
			if not info:
				continue

			pname, video_ntiid, video_path = info
			parser = component.getUtility(media_interfaces.IVideoTranscriptParser, name=pname)
			with open(video_path, "r") as source:
				transcript = parser.parse(source)

			video_ntiid = unicode(video_ntiid)
			for e in transcript:
				self.index_transcript_entry(writer, containerId, video_ntiid, e, language)
				count += 1
		return count

_DefaultWhooshVideoTranscriptIndexer = _WhooshVideoTranscriptIndexer
