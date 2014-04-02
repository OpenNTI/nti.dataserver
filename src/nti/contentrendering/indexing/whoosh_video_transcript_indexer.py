# -*- coding: utf-8 -*-
"""
Whoosh video transcript indexer.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import time
from datetime import datetime

from zope import component
from zope import interface

from nti.contentprocessing import split_content
from nti.contentprocessing import get_content_translation_table

from nti.contentrendering import ConcurrentExecutor

from nti.contentsearch.constants import vtrans_prefix
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.common import videotimestamp_to_datetime

from nti.utils.property import alias

from . import node_utils
from . import termextract
from . import content_utils
from . import interfaces as cridxr_interfaces
from ..media import interfaces as media_interfaces
from . import whoosh_common_indexer as common_indexer

_video_types = (u'application/vnd.nextthought.ntivideo')

_media_transcript_types = (u'application/vnd.nextthought.mediatranscript',)

_video_source_types = (u'application/vnd.nextthought.videosource',)

class _Video(object):

	lang = alias('language')

	def __init__(self, parser_name, video_ntiid, video_path, title=None, language='en'):
		self.title = title
		self.transcript = None
		self.containerId = None
		self.language = language
		self.video_path = video_path
		self.parser_name = parser_name
		self.video_ntiid = video_ntiid

	@property
	def path(self):
		return self.video_path

	@property
	def parser(self):
		return self.parser_name

	@property
	def ntiid(self):
		return self.video_ntiid

	def __str__(self):
		return "%s,%s" % (self.ntiid, self.path)

	def __repr__(self):
		return "%s(%s,%s,%s)" % (self.__class__, self.ntiid, self.path, self.language)

	def __eq__(self, other):
		try:
			return self is other or (self.ntiid == other.ntiid
									 and self.path == self.path)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.path)
		xhash ^= hash(self.ntiid)
		return xhash

def _parse_video_source(video):
	parser = component.getUtility(media_interfaces.IVideoTranscriptParser,
								  name=video.parser)
	with open(video.path, "r") as source:
		transcript = parser.parse(source)
	return video, transcript

def _prepare_entry(entry, lang):
	content = entry.transcript
	if content:
		table = get_content_translation_table(lang)
		entry.content = unicode(content_utils.sanitize_content(content, table=table))
		tokenized_words = split_content(entry.content, lang)
		entry.keywords = termextract.extract_key_words(tokenized_words, lang=lang)
		entry.processed = True
	else:
		entry.processed = False
	return entry

def _parse_and_prepare(video):
	result = []
	video, transcript = _parse_video_source(video)
	for entry in transcript:
		_prepare_entry(entry, video.language)
		result.append((video, entry))
	return result

@interface.implementer(cridxr_interfaces.IWhooshVideoTranscriptIndexer)
class _WhooshVideoTranscriptIndexer(common_indexer._BasicWhooshIndexer):

	def get_schema(self, name='en'):
		creator = \
			component.getUtility(search_interfaces.IWhooshVideoTranscriptSchemaCreator,
								 name=name)
		return creator.create()

	@classmethod
	def _get_video_transcript_parser_names(cls):
		utils = component.getUtilitiesFor(media_interfaces.IVideoTranscriptParser)
		result = {x for x, _ in utils}
		return result

	def _get_topic_map(self, dom):
		result = {}
		for topic_el in dom.getElementsByTagName('topic'):
			ntiid = topic_el.getAttribute('ntiid')
			if ntiid:
				result[ntiid] = topic_el
		return result

	def _find_toc_videos(self, topic_map):
		result = {}
		for topic_ntiid, topic_el in topic_map.items():
			for obj in topic_el.getElementsByTagName('object'):
				mimeType = obj.getAttribute('mimeType')
				if mimeType != u'application/vnd.nextthought.ntivideo':
					continue
				ntiid = obj.getAttribute('ntiid')
				if ntiid and topic_ntiid:
					result[ntiid] = topic_ntiid  # Pick one contaienr
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

	def _capture_param(self, p, params):
		if p.tag == 'param':
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
				self._capture_param(p, params)

			if 'src' in params and 'lang' not in params:
				params['lang'] = data_lang

		return params if 'src' in params else None

	def _process_videosource(self, node):
		params = {}
		type_ = node_utils.get_attribute(node, 'type')
		if type_ in _video_source_types:
			for p in node.iterchildren():
				self._capture_param(p, params)
		return params if params else None

	def _process_ntivideo(self, topic, node):
		type_ = node_utils.get_attribute(node, 'type')
		if not type_ or type_ not in _video_types:
			return ()

		params = {}
		transcripts = []
		video_sources = []
		video_ntiid = node_utils.get_attribute(node, 'data-ntiid')
		for p in node.iterchildren():
			if p.tag == 'object':
				# check for transcript
				trax = self._process_transcript(p)
				if trax:
					transcripts.append(trax)

				# check for video sources
				vidsrc = self._process_videosource(p)
				if vidsrc:
					video_sources.append(vidsrc)
			else:
				self._capture_param(p, params)

		title = params.get('title', u'')

		# makre sure we have a ntiid for the video
		if not video_ntiid:
			video_ntiid = params.get('data-ntiid', params.get('ntiid'))  or u''

		content_path = os.path.dirname(topic.location)
		parser_names = self._get_video_transcript_parser_names()

		result = ()
		if not transcripts and video_sources:
			# process legacy spec
			language = node_utils.get_attribute(node, 'data-lang') or \
					   params.get('data-lang', params.get('lang')) or 'en'

			for vrdsrc in video_sources:
				bases = {video_ntiid, vrdsrc.get('subtitle', None),
						 params.get('subtitle')}
				if vrdsrc.get('service', vrdsrc.get('type', u'')).lower() == 'youtube':
					bases.add(vrdsrc.get('source'))
				bases.discard(None)

				vid_tupl = self._find_video_transcript(content_path, bases, parser_names)
				if vid_tupl:
					parser_name, video_path = vid_tupl
					result = (_Video(parser_name, video_ntiid, video_path,
									title, language),)
					break
		else:
			result = []
			for t in transcripts:
				location = t['src']
				ext = os.path.splitext(location)[1][1:] or ''
				video_path = os.path.join(content_path, location)
				if os.path.exists(video_path) and ext.lower() in parser_names:
					language = t['lang']
					vid = _Video(ext.lower(), video_ntiid, video_path, title, language)
					result.append(vid)

		return result

	def index_transcript_entry(self, writer, containerId, video_id, title,
							   entry, language=u'en'):

		if not getattr(entry, 'processed', False):
			_prepare_entry(entry, language)

		if not entry.processed:
			return False

		try:
			last_modified = datetime.fromtimestamp(time.time())
			end_ts = entry.end_timestamp
			start_ts = entry.start_timestamp
			writer.add_document(containerId=containerId,
								videoId=video_id,
								language=language,
								title=title,
								content=entry.content,
								quick=entry.content,
								keywords=entry.keywords,
								last_modified=last_modified,
								end_timestamp=videotimestamp_to_datetime(end_ts),
								start_timestamp=videotimestamp_to_datetime(start_ts))
			return True
		except Exception:
			writer.cancel()
			raise

	def get_index_name(self, book, indexname=None):
		indexname = \
			super(_WhooshVideoTranscriptIndexer, self).get_index_name(book, indexname)
		indexname = vtrans_prefix + indexname
		return indexname

	def process_topic(self, idxspec, topic, writer, toc_videos={}):
		videos = set()
		containerId = unicode(topic.ntiid) or u''

		for n in topic.dom(b'object'):
			nti_vids = self._process_ntivideo(topic, n)
			if nti_vids:
				videos.update(nti_vids)

		for video in videos:
			video.containerId = toc_videos.get(video.ntiid, containerId)
		return videos

	def _process_video_source(self, videos):
		result = []
		videos = [videos] if isinstance(videos, _Video) else videos
		with ConcurrentExecutor() as executor:
			for lst in executor.map(_parse_and_prepare, videos):
				result.extend(lst)
		return result

	def _parse_and_index_videos(self, videos, writer):
		count = 0
		zipped = self._process_video_source(videos)
		for video, entry in zipped:
			if self.index_transcript_entry(writer,
										   unicode(video.containerId),
										   unicode(video.ntiid),
										   unicode(video.title),
										   entry,
										   unicode(video.language)):
				count += 1
		return count

	def process_book(self, idxspec, writer, *args, **kwargs):
		# find videos in toc
		if idxspec:
			dom = idxspec.book.toc.dom
			topic_map = self._get_topic_map(dom)
			toc_videos = self._find_toc_videos(topic_map)
		else:
			toc_videos = {}

		# capture all videos to parse
		result = set()
		toc = idxspec.book.toc
		def _loop(topic):
			videos = self.process_topic(idxspec, topic, writer, toc_videos)
			result.update(videos)
			# parse children
			for t in topic.childTopics:
				_loop(t)
		_loop(toc.root_topic)

		# parse and index
		count = self._parse_and_index_videos(result, writer)
		return count

_DefaultWhooshVideoTranscriptIndexer = _WhooshVideoTranscriptIndexer
