#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
from datetime import datetime

from zope import component

from nti.common.property import alias

from nti.contentindexing.utils import sanitize_content

from nti.contentprocessing import tokenize_content
from nti.contentprocessing import get_content_translation_table

from nti.contentrendering import ConcurrentExecutor

from . _utils import get_attribute

from ._extract import extract_key_words

from .common_indexer import BasicWhooshIndexer

_media_transcript_types = (u'application/vnd.nextthought.mediatranscript',)

class _Media(object):

	lang = alias('language')

	def __init__(self, parser_name, ntiid, path, title=None, language='en'):
		self.path = path
		self.title = title
		self.ntiid = ntiid
		self.transcript = None
		self.containerId = None
		self.language = language
		self.parser_name = parser_name

	@property
	def parser(self):
		return self.parser_name

	def __str__(self):
		return "%s,%s" % (self.ntiid, self.path)

	def __repr__(self):
		return "%s(%s,%s,%s)" % (self.__class__.__name__,
								 self.ntiid,
								 self.path,
								 self.language)

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

def _parse_media_source(interface, media):
	parser = component.getUtility(interface, name=media.parser)
	with open(media.path, "r") as source:
		transcript = parser.parse(source)
	return media, transcript

def _prepare_entry(entry, lang):
	content = entry.transcript
	if content:
		table = get_content_translation_table(lang)
		entry.content = unicode(sanitize_content(content, table=table))
		tokenized_words = tokenize_content(entry.content, lang)
		entry.keywords = extract_key_words(tokenized_words, lang=lang)
		entry.processed = True
	else:
		entry.processed = False
	return entry

def _parse_and_prepare(interface, media):
	result = []
	media, transcript = _parse_media_source(interface, media)
	for entry in transcript:
		_prepare_entry(entry, media.language)
		result.append((media, entry))
	return result

class WhooshMediaTranscriptIndexer(BasicWhooshIndexer):

	media_cls = _Media
	media_prefix = None
	media_mimeType = None
	media_source_types = ()
	media_transcript_schema_creator = None
	media_transcript_parser_interface = None

	def get_schema(self, name='en'):
		creator = component.getUtility(self.media_transcript_schema_creator, name=name)
		return creator.create()

	def _get_media_transcript_parser_names(self):
		utils = component.getUtilitiesFor(self.media_transcript_parser_interface)
		result = {x for x, _ in utils}
		return result

	def _get_topic_map(self, dom):
		result = {}
		for topic_el in dom.getElementsByTagName('topic'):
			ntiid = topic_el.getAttribute('ntiid')
			if ntiid:
				result[ntiid] = topic_el
		return result

	def _find_media_in_toc(self, topic_map):
		result = {}
		for topic_ntiid, topic_el in topic_map.items():
			for obj in topic_el.getElementsByTagName('object'):
				mimeType = obj.getAttribute('mimeType')
				if mimeType == self.media_mimeType:
					ntiid = obj.getAttribute('ntiid')
					if ntiid and topic_ntiid:
						result[ntiid] = topic_ntiid  # Pick one contaienr
		return result

	def _find_media_transcript(self, base_location, bases, parser_names):
		for location in ('.', '../Transcripts', './Transcripts'):
			path = os.path.join(base_location, location)
			if not os.path.exists(path):
				continue
			for parser in parser_names:
				ext = '.' + parser
				for basename in bases:
					fname = os.path.splitext(basename)[0] + ext
					media_path = os.path.join(path, fname)
					if os.path.exists(media_path):
						return parser, media_path
		return None

	def _capture_param(self, p, params):
		if p.tag == 'param':
			name = get_attribute(p, 'name')
			value = get_attribute(p, 'value')
			if name and value:
				params[name] = value

	def _process_transcript(self, node):
		params = {}
		type_ = get_attribute(node, 'type')
		if type_ in _media_transcript_types:
			data_lang = get_attribute(node, 'data-lang') or 'en'
			for p in node.iterchildren():
				self._capture_param(p, params)

			if 'src' in params and 'lang' not in params:
				params['lang'] = data_lang

		return params if 'src' in params else None

	def _process_mediaource(self, node):
		params = {}
		type_ = get_attribute(node, 'type')
		if type_ in self.media_source_types:
			for p in node.iterchildren():
				self._capture_param(p, params)
		return params if params else None

	def _process_ntimedia(self, topic, node):
		type_ = get_attribute(node, 'type')
		if type_ != self.media_mimeType:
			return ()

		params = {}
		transcripts = []
		media_sources = []
		media_ntiid = get_attribute(node, 'data-ntiid')
		for p in node.iterchildren():
			if p.tag == 'object':
				# check for transcript
				trax = self._process_transcript(p)
				if trax:
					transcripts.append(trax)

				# check for media sources
				midsrc = self._process_mediaource(p)
				if midsrc:
					media_sources.append(midsrc)
			else:
				self._capture_param(p, params)

		title = params.get('title', u'')

		# makre sure we have a ntiid for the media
		if not media_ntiid:
			media_ntiid = params.get('data-ntiid', params.get('ntiid'))  or u''

		content_path = os.path.dirname(topic.location)
		parser_names = self._get_media_transcript_parser_names()

		result = ()
		if not transcripts and media_sources:
			# process legacy spec
			language = get_attribute(node, 'data-lang') or \
					   params.get('data-lang', params.get('lang')) or 'en'

			for midsrc in media_sources:
				bases = {media_ntiid,
						 midsrc.get('subtitle', None),
						 params.get('subtitle')}

				if midsrc.get('service', midsrc.get('type', u'')).lower() == 'youtube':
					bases.add(midsrc.get('source'))
				bases.discard(None)

				mid_tupl = self._find_media_transcript(content_path, bases, parser_names)
				if mid_tupl:
					parser_name, media_path = mid_tupl
					result = (self.media_cls(parser_name,
											 media_ntiid,
											 media_path,
											 title,
											 language),)
					break
		else:
			result = []
			for transcript in transcripts:
				location = transcript['src']
				ext = os.path.splitext(location)[1][1:] or ''
				media_path = os.path.join(content_path, location)
				if os.path.exists(media_path) and ext.lower() in parser_names:
					language = transcript['lang']
					mid = self.media_cls(ext.lower(),
										 media_ntiid,
										 media_path,
										 title,
										 language)
					result.append(mid)

		return result

	def _add_document(self, writer, containerId, media_id, language, title, content,
					  keywords, last_modified, start_ts, end_ts):
		raise NotImplementedError()

	def index_transcript_entry(self, writer, containerId, media_id, title,
							   entry, language=u'en'):

		if not getattr(entry, 'processed', False):
			_prepare_entry(entry, language)

		if not entry.processed:
			return False

		try:
			last_modified = datetime.now()
			end_ts = entry.end_timestamp
			start_ts = entry.start_timestamp
			self._add_document(writer,
						 	   containerId=containerId,
							   media_id=media_id,
							   language=language,
							   title=title,
							   content=entry.content,
							   keywords=entry.keywords,
							   last_modified=last_modified,
							   end_ts=end_ts,
							   start_ts=start_ts)
			return True
		except Exception:
			writer.cancel()
			raise

	def get_index_name(self, book, indexname=None):
		cls = WhooshMediaTranscriptIndexer
		indexname = super(cls, self).get_index_name(book, indexname)
		indexname = self.media_prefix + indexname
		return indexname

	def process_topic(self, idxspec, topic, writer, toc_media={}):
		result = set()
		containerId = unicode(topic.ntiid) or u''

		for n in topic.dom(b'object'):
			nti_mids = self._process_ntimedia(topic, n)
			if nti_mids:
				result.update(nti_mids)

		for media in result:
			media.containerId = toc_media.get(media.ntiid, containerId)
		return result

	def _process_media_source(self, media):
		result = []
		media = [media] if isinstance(media, self.media_cls) else media
		ifaces = [self.media_transcript_parser_interface] * len(media)
		with ConcurrentExecutor() as executor:
			for lst in executor.map(_parse_and_prepare, ifaces, media):
				result.extend(lst)
		return result

	def _parse_and_index_media(self, media, writer):
		count = 0
		zipped = self._process_media_source(media)
		for media, entry in zipped:
			if self.index_transcript_entry(writer,
										   unicode(media.containerId),
										   unicode(media.ntiid),
										   unicode(media.title),
										   entry,
										   unicode(media.language)):
				count += 1
		return count

	def process_book(self, idxspec, writer, *args, **kwargs):
		# find media in toc
		if idxspec:
			dom = idxspec.book.toc.dom
			topic_map = self._get_topic_map(dom)
			toc_media = self._find_media_in_toc(topic_map)
		else:
			toc_media = {}

		# capture all media to parse
		result = set()
		toc = idxspec.book.toc
		def _loop(topic):
			media = self.process_topic(idxspec, topic, writer, toc_media)
			result.update(media)
			# parse children
			for t in topic.childTopics:
				_loop(t)
		_loop(toc.root_topic)

		# parse and index
		count = self._parse_and_index_media(result, writer)
		return count

_WhooshMediaTranscriptIndexer = WhooshMediaTranscriptIndexer #BWC
