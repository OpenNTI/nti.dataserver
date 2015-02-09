#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import simplejson as json
from collections import defaultdict
from collections import OrderedDict

from zope import component
from zope import interface

from plasTeX.Base.LaTeX import Document as LaTexDocument

from nti.common.sets import OrderedSet

from ._utils import _render_children

from ...interfaces import IRenderedBook
from ...interfaces import INTIAudioExtractor
from ...interfaces import INTIVideoExtractor

@component.adapter(IRenderedBook)
class _NTIMediaExtractor(object):

	ntimedia = u'ntimedia'
	ntimediaref = u'ntimediaref'
	index_file  = u'media_index.json'
	media_mimeType = u'application/vnd.nextthought.ntimedia'
	index_mimeType = u'application/vnd.nextthought.mediaindex'

	def __init__(self, book=None):
		pass

	def transform(self, book, savetoc=True, outpath=None):
		outpath = outpath or book.contentLocation
		outpath = os.path.expanduser(outpath)
		
		dom = book.toc.dom
		media_els = book.document.getElementsByTagName(self.ntimedia)
		reference_els = book.document.getElementsByTagName(self.ntimediaref)
		if not (reference_els or media_els):
			return

		# cache topics
		topic_map = self._get_topic_map(dom)
		self._process_references(dom, reference_els, topic_map)
		self._process_media_els(dom, media_els, outpath, topic_map)
		if savetoc:
			book.toc.save()

	def _get_topic_map(self, dom):
		result = {}
		for topic_el in dom.getElementsByTagName('topic'):
			ntiid = topic_el.getAttribute('ntiid')
			if ntiid:
				result[ntiid] = topic_el
		return result

	def _add_2_od(self, od, key, value):
		s = od.get(key)
		if s is None:
			s = od[key] = OrderedSet()
		s.add(value)
		
	def _find_toc_media(self, topic_map):
		result = OrderedDict()
		inverted = OrderedDict()
		for topic_ntiid, topic_el in topic_map.items():
			for obj in topic_el.getElementsByTagName('object'):
				if obj.getAttribute('mimeType') != self.media_mimeType:
					continue
				ntiid = obj.getAttribute('ntiid')
				if ntiid and topic_ntiid:
					self._add_2_od(result, ntiid, topic_ntiid)
					self._add_2_od(inverted, topic_ntiid, ntiid)
		return result, inverted
	
	def _process_media(self, dom, media, topic_map):
		entry = {'sources':[], 'transcripts':[]}

		entry['ntiid'] = media.ntiid
		entry['creator'] = media.creator
		if hasattr(media.title, 'textContent'):
			entry['title'] = media.title.textContent
		else:
			entry['title'] = media.title

		entry['mimeType'] = media.mimeType

		for transcript in media.getElementsByTagName('mediatranscript'):
			val = {}
			val['src'] = transcript.raw.url
			val['srcjsonp'] = transcript.wrapped.url
			val['lang'] = transcript.attributes['lang']
			val['type'] = transcript.transcript_mime_type
			val['purpose'] = transcript.attributes['purpose']
			entry['transcripts'].append(val)

		# find parent document
		parent = media.parentNode
		while parent is not None and not isinstance(parent, LaTexDocument.document):
			ntiid = getattr(parent, 'ntiid', None) or u''
			if ntiid in topic_map:
				break
			else:
				parent = parent.parentNode

		container = getattr(parent, 'ntiid', None) if parent else None
		return entry, container

	def _process_media_els(self, dom, elements, outpath, topic_map):
		filename = self.index_file
		
		## We'd like these things, especially Containers, to be
		## ordered as they are in the source. We can preserve it here,
		## if we try. The original list of elements must be in order
		## of how they appear in the source, and it is more-or-less.

		## In practice, it's not nearly that simple because of the
		## "overrides". In practice, all ntivideo elements are children
		## of the document for some reason, and ntivideoref elements
		## are scattered about through the content to refer to these
		## elements. In turn, these ntivideoref elements get added to
		## the ToC dom (NOT the content dom) as "<object>" tags...we go
		## through and "re-parent" ntivideo elements in the Containers
		## collection based on where references appear to them

		## Therefore, we maintain yet another parallel data structure
		## recording the original iteration order of the elements,
		## and at the very end, when we have assigned videos
		## to containers, we sort that list by this original order.
		
		items = {}
		inverted = defaultdict(set)
		containers = defaultdict(set)
		original_media_iteration_order = []
		
		## parse all elements
		for element in elements:
			## build media elemenet
			media, containerId = self._process_media(dom, element, topic_map)
			ntiid = media['ntiid']
			items[ntiid] = media
			
			## add to tracking maps
			if containerId:
				inverted[ntiid].add(containerId)
				containers[containerId].add(ntiid)

			## keep sort order for default containers
			original_media_iteration_order.append(ntiid)
			
		## add video objects to toc and compute re-parent locations based on references
		overrides = defaultdict(set)
		doc_ntiid = dom.documentElement.getAttribute('ntiid')
		media_in_toc, inverted_media_in_toc = self._find_toc_media(topic_map)
		for mid_ntiid, cnt_ids in inverted.items():
			toc_entries = media_in_toc.get(mid_ntiid)
			if toc_entries:
				for toc_container_id in toc_entries:
					overrides[mid_ntiid].add(toc_container_id)
			else:
				for container in cnt_ids:
					if container == doc_ntiid:
						parent = dom.documentElement
					else:
						parent = topic_map.get(container)
						if parent is None:
							continue

					# create new elemenet
					media = items.get(mid_ntiid)
					obj_el = dom.createElement('object')
					label = media.get('title') if media else None
					obj_el.setAttribute(u'label', label or u'')
					obj_el.setAttribute(u'ntiid', mid_ntiid)
					obj_el.setAttribute(u'mimeType', self.media_mimeType)

					# add to parent
					parent.childNodes.append(obj_el)

		## apply overrides, remove all existing. TOC always win
		for mid_ntiid in overrides.keys():
			for container in containers.values():
				container.discard(mid_ntiid)

		for mid_ntiid, cnt_ids in overrides.items():
			for container in cnt_ids:
				containers[container].add(mid_ntiid)

		## remove any empty elements
		for ntiid, mid_ids in list(containers.items()):
			if not mid_ids:
				containers.pop(ntiid)
			else:
				sort_order = inverted_media_in_toc.get(ntiid) or \
							 original_media_iteration_order
				## Make JSON Serializable (a plain list object),
				## and also sort according to original iteration order
				## either from the TOC override or the default media order
				containers[ntiid] = [orig_media_id
									 for orig_media_id in sort_order
									 if orig_media_id in mid_ids]

		## Write the normal version
		media_index = {'Items': items, 'Containers':containers}
		with open(os.path.join(outpath, filename), "wb") as fp:
			json.dump(media_index, fp, indent=4)

		## Write the JSONP version
		with open(os.path.join(outpath, filename + 'p'), "wb") as fp:
			fp.write('jsonpReceiveContent(')
			json.dump({'ntiid': dom.childNodes[0].getAttribute('ntiid'),
					   'Content-Type': 'application/json',
					   'Content-Encoding': 'json',
					   'content': media_index,
					   'version': '1'}, fp, indent=4)
			fp.write(');')

		toc_el = dom.createElement('reference')
		toc_el.setAttribute('href', filename)
		toc_el.setAttribute('type', self.index_mimeType)

		dom.childNodes[0].appendChild(toc_el)

	def _process_references(self, dom, els, topic_map):
		for el in els:
			if el.parentNode:
				lesson_el = None
				
				## Discover the nearest topic in the toc that is a 'course' node
				parent_el = el.parentNode
				if 	hasattr(parent_el, 'ntiid') and \
					parent_el.tagName.startswith('course'):
					lesson_el = topic_map.get(parent_el.ntiid)

				while lesson_el is None and parent_el.parentNode is not None:
					parent_el = parent_el.parentNode
					if hasattr(parent_el, 'ntiid') and \
						parent_el.tagName.startswith('course'):
						lesson_el = topic_map.get(parent_el.ntiid)

				media_title = getattr(el.media, 'title', u'')
				title = _render_children(el.media.renderer, media_title)

				toc_el = dom.createElement('object')
				toc_el.setAttribute('label', title)

				for name in ('poster', 'ntiid', 'mimeType'):
					if hasattr(el.media, name):
						toc_el.setAttribute(name, getattr(el.media , name, None))

				if hasattr(el, 'visibility'):
					toc_el.setAttribute('visibility', el.visibility)

				if lesson_el is not None:
					lesson_el.appendChild(toc_el)

@interface.implementer(INTIVideoExtractor)
class _NTIVideoExtractor(_NTIMediaExtractor):

	ntimedia = u'ntivideo'
	ntimediaref = u'ntivideoref'
	index_file = u"video_index.json"
	media_mimeType = u'application/vnd.nextthought.ntivideo'
	index_mimeType = u'application/vnd.nextthought.videoindex'

	def _process_media(self, dom, video, topic_map):
		entry, container = super(_NTIVideoExtractor, self)._process_media(dom, video,
																		  topic_map)
		
		entry['description'] = video.description
		entry['closedCaptions'] = video.closed_caption
		if hasattr(video, 'slidedeck'):
			entry['slidedeck'] = video.slidedeck

		for source in video.getElementsByTagName('ntivideosource'):
			val = {'source':[], 'type':[]}

			val['width'] = source.width
			val['poster'] = source.poster
			val['height'] = source.height
			val['service'] = source.service
			val['thumbnail'] = source.thumbnail

			if source.service == 'html5':
				val['type'].append('video/mp4')
				val['type'].append('video/webm')
				val['source'].append(source.src['mp4'])
				val['source'].append(source.src['webm'])
			elif source.service == 'youtube':
				val['type'].append('video/youtube')
				val['source'].append(source.src['other'])
			elif source.service == 'kaltura':
				val['type'].append('video/kaltura')
				val['source'].append(source.src['other'])
			elif source.service == 'vimeo':
				val['type'].append('video/vimeo')
				val['source'].append(source.src['other'])
			entry['sources'].append(val)

		return entry, container

@interface.implementer(INTIAudioExtractor)
class _NTIAudioExtractor(_NTIMediaExtractor):

	ntimedia = u'ntiaudio'
	ntimediaref = u'ntiaudioref'
	index_file  = u'audio_index.json'
	media_mimeType = u'application/vnd.nextthought.ntiaudio'
	index_mimeType = u'application/vnd.nextthought.audioindex'

	def _process_media(self, dom, audio, topic_map):
		entry, container = super(_NTIAudioExtractor, self)._process_media(dom, audio,
																		  topic_map)
		entry['description'] = getattr(audio, 'description', None)
		for source in audio.getElementsByTagName('ntiaudiosource'):
			val = {'source':[], 'type':[]}
			val['service'] = source.service
			val['thumbnail'] = source.thumbnail
			if source.service == 'html5':
				val['type'].append('audio/mp3')
				val['type'].append('audio/wav')
				val['source'].append(source.src['mp3'])
				val['source'].append(source.src['wav'])
			entry['sources'].append(val)
		return entry, container
