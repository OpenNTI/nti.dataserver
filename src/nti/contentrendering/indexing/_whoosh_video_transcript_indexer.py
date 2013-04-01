# -*- coding: utf-8 -*-
"""
Whoosh video transcript indexers.

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

from nti.contentsearch import interfaces as search_interfaces

from . import _node_utils as nu
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
			type_ = nu.get_attribute(obj, 'type')
			itemprop = nu.get_attribute(obj, 'itemprop')
			if itemprop == 'nti-slide-video' and type_ == 'application/vnd.nextthought.slidevideo':
				result = {}
				for p in obj.iterchildren():
					if p.tag != 'param': continue
					name = nu.get_attribute(p, 'name')
					value = nu.get_attribute(p, 'value')
					if name and value:
						result[name] = value
				break
		return result

	def _get_externalvideo_info(self, topic, node):
		info = self._parse_externalvideo_node(node)
		if not info:
			return

		video_id = info.get('id')
		video_type = info.get('type')
		video_ntiid = info.get('ntiid')
		parser_names = self._get_video_transcript_parser_names()
		content_path = os.path.dirname(topic.location)

		bases = [video_ntiid]
		if video_type == 'youtube':
			bases.append(video_id)

		# search for filenames
		for pn in parser_names:
			ext = '.' + pn
			for basename in bases:
				if not basename: continue
				fname = basename + ext
				vpath = os.path.join(content_path, fname)
				if os.path.exists(vpath):
					return (pn, video_ntiid, vpath)
		return None

	def index_transcript_entry(self, writer, containerId, video_id, entry, language=u'en'):
		try:
			content = entry.transcript
			table = get_content_translation_table(language)
			content = unicode(content_utils.sanitize_content(content, table=table))
			last_modified = datetime.fromtimestamp(time.time())
			writer.add_document(containerId=containerId,
								videoId=video_id,
								content=content,
								quick=content,
								start_timestamp=unicode(entry.start_timestamp),
								end_timestamp=unicode(entry.end_timestamp),
								last_modified=last_modified)
		except Exception:
			writer.cancel()
			raise

	def get_index_name(self, book, indexname=None):
		indexname = super(_WhooshVideoTranscriptIndexer, self).get_index_name(book, indexname)
		indexname = "vtrans_%s" % indexname
		return indexname

	def process_topic(self, idxspec, topic, writer, language='en'):
		count = 0
		containerId = unicode(topic.ntiid)
		for n in topic.dom(b'div').filter(b'.externalvideo'):
			info = self._get_externalvideo_info(topic, n)
			if not info:
				continue

			pname, video_ntiid, vpath = info
			parser = component.getUtility(media_interfaces.IVideoTranscriptParser, name=pname)
			with open(vpath, "r") as source:
				transcript = parser.parse(source)

			video_ntiid = unicode(video_ntiid)
			for e in transcript:
				self.index_transcript_entry(writer, containerId, video_ntiid, e, language)
				count += 1
		return count

_DefaultWhooshVideoTranscriptIndexer = _WhooshVideoTranscriptIndexer
