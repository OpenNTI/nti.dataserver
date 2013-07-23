# -*- coding: utf-8 -*-
"""
Whoosh video transcript indexer.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import time
import urlparse
import collections
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

_Video = collections.namedtuple('Video', 'parser_name, video_ntiid, video_path, language')

_video_types = (u'application/vnd.nextthought.ntivideo', u'application/vnd.nextthought.slidevideo',
				u'application/vnd.nextthought.ntislidevideo')

_media_transcript_types = (u'application/vnd.nextthought.mediatranscript',)

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

	def _find_video_transcript(self, base_location, bases, parser_names):
		for location in ('.', '../Transcripts', './Transcripts'):
			path = os.path.join(base_location, location)
			if not os.path.exists(path):
				continue
			for pn in parser_names:
				ext = '.' + pn
				for basename in bases:
					fname = os.path.splitext(basename)[0] + ext
					video_path = os.path.join(path, fname)
					if os.path.exists(video_path):
						return pn, video_path
		return None

	def _get_externalvideo_info(self, topic, node):
		content_path = os.path.dirname(topic.location)
		video_ntiid = node_utils.get_attribute(node, 'id')
		parser_names = self._get_video_transcript_parser_names()
		language = node_utils.get_attribute(node, 'language') or 'en'
		for obj in node.iterchildren():
			if obj.tag == 'iframe':
				src = node_utils.get_attribute(obj, 'src')
				if src:
					path = urlparse.urlparse(src).path
					vid = os.path.splitext(os.path.basename(path))[0]
					language = node_utils.get_attribute(obj, 'language') or language
					vid_tupl = self._find_video_transcript(content_path, [vid], parser_names)
					if vid_tupl:
						parser_name, video_path = vid_tupl
						return _Video(parser_name, video_ntiid, video_path, language)
		return None

	def _capture_param(self, p, params):
		name = node_utils.get_attribute(p, 'name')
		value = node_utils.get_attribute(p, 'value')
		if name and value:
			params[name] = value

	def _process_transcript(self, node):
		params = {}
		type_ = node_utils.get_attribute(node, 'type')
		if type_ in _media_transcript_types:
			data_lang = node_utils.get_attribute(node, 'data-lang') or 'en'
			for p in node.iterchildren():
				if p.tag == 'param':
					self._capture_param(p, params)
		
			if 'src' in params and 'lang' not in params:
				params['lang'] = data_lang
		
		return params if 'src' in params else None

	def _process_ntivideo(self, topic, node):
		type_ = node_utils.get_attribute(node, 'type')
		if type_ not in _video_types:
			return ()

		params = {}
		transcripts = []
		video_ntiid = node_utils.get_attribute(node, 'data-ntiid')
		for p in node.iterchildren():
			if p.tag == 'param':
				self._capture_param(p, params)
			elif p.tag == 'object':
				t = self._process_transcript(p)
				if t: transcripts.append(t)
				
		# makre sure we have a ntiid for the video
		if not video_ntiid:
			video_ntiid = params.get('data-ntiid', params.get('ntiid'))  or u''

		content_path = os.path.dirname(topic.location)
		parser_names = self._get_video_transcript_parser_names()

		result = ()
		if not transcripts:
			# process legacy spec
			language = node_utils.get_attribute(node, 'data-lang') or \
					   params.get('data-lang', params.get('lang')) or 'en'

			# collect video-base names
			bases = {video_ntiid, params.get('subtitle', None)}
			if params.get('type') == 'youtube':
				bases.add(params.get('id'))
			bases.discard(None)

			vid_tupl = self._find_video_transcript(content_path, bases, parser_names)
			if vid_tupl:
				parser_name, video_path = vid_tupl
				result = (_Video(parser_name, video_ntiid, video_path, language),)
		else:
			result = []
			for t in transcripts:
				location = t['src']
				ext = os.path.splitext(location)[1][1:] or ''
				video_path = os.path.join(content_path, location)
				if os.path.exists(video_path) and ext.lower() in parser_names:
					language = t['lang']
					vid = _Video(ext.lower(), video_ntiid, video_path, language)
					result.append(vid)

		return result

	def index_transcript_entry(self, writer, containerId, video_id, entry, language=u'en'):
		content = entry.transcript
		if not content:
			return False

		try:
			table = get_content_translation_table(language)
			last_modified = datetime.fromtimestamp(time.time())
			content = unicode(content_utils.sanitize_content(content, table=table))
			writer.add_document(containerId=containerId,
								videoId=video_id,
								language=language,
								content=content,
								quick=content,
								last_modified=last_modified,
								end_timestamp=videotimestamp_to_datetime(entry.end_timestamp),
								start_timestamp=videotimestamp_to_datetime(entry.start_timestamp))
			return True
		except Exception:
			writer.cancel()
			raise

	def get_index_name(self, book, indexname=None):
		indexname = super(_WhooshVideoTranscriptIndexer, self).get_index_name(book, indexname)
		indexname = vtrans_prefix + indexname
		return indexname

	def process_topic(self, idxspec, topic, writer):
		videos = set()
		containerId = unicode(topic.ntiid) or u''

		for n in topic.dom(b'div').filter(b'.externalvideo'):
			info = self._get_externalvideo_info(topic, n)
			if info:
				videos.add(info)

		for n in topic.dom(b'object'):
			nti_vids = self._process_ntivideo(topic, n)
			if nti_vids:
				videos.update(nti_vids)

		return (videos, containerId)

	def _parse_and_index_videos(self, videos, containerId, writer):
		if isinstance(videos, _Video):
			videos = [videos]

		count = 0
		for video in videos:
			pname, video_ntiid, video_path, lang = video
			parser = component.getUtility(media_interfaces.IVideoTranscriptParser, name=pname)
			with open(video_path, "r") as source:
				transcript = parser.parse(source)

			video_ntiid = unicode(video_ntiid)
			for e in transcript:
				if self.index_transcript_entry(writer, containerId, video_ntiid, e, lang):
					count += 1
		return count

	def process_book(self, idxspec, writer, *args, **kwargs):
		# capture all videos to parse
		result = {}
		toc = idxspec.book.toc
		def _loop(topic):
			videos, containerId = self.process_topic(idxspec, topic, writer)
			for video in videos:
				if video not in result:
					result[video] = containerId
			# parse children
			for t in topic.childTopics:
				_loop(t)
		_loop(toc.root_topic)

		# parse and index
		count = 0
		for video, containerId in result.items():
			count += self._parse_and_index_videos(video, containerId, writer)
		return count

_DefaultWhooshVideoTranscriptIndexer = _WhooshVideoTranscriptIndexer
