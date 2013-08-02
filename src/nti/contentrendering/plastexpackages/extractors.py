#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Book extractors

$Id: slidedeckextractor.py 21266 2013-07-23 21:52:35Z sean.jones $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import simplejson
import collections

from zope import component
from zope import interface

from plasTeX.Base.LaTeX import Document as LaTexDocument

from nti.contentrendering import interfaces as crd_interfaces

@interface.implementer(crd_interfaces.IRelatedWorkExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _RelatedWorkExtractor(object):

	def __init__(self, book=None):
		pass

	def transform( self, book ):
		lesson_els = book.document.getElementsByTagName( 'courselesson' )
		related_els = book.document.getElementsByTagName( 'relatedwork' )
		dom = book.toc.dom
		if lesson_els or related_els:
			self._process_lessons(dom, lesson_els)
			self._process_related(dom, related_els)
			dom.childNodes[0].setAttribute('xmlns:content', "http://www.nextthought.com/toc")
			book.toc.save()

	def _process_lessons(self, dom, els):
		for el in els:
			ref_els = el.getElementsByTagName('relatedworkref')
			if ref_els:
				lesson_el = None

				# Determine which topic represents the lesson
				topic_els = dom.getElementsByTagName('topic')
				for topic_el in topic_els:
					if topic_el.getAttribute('ntiid') == el.ntiid:
						lesson_el = topic_el

				for ref_el in ref_els:
					if ref_el.relatedwork.iconResource is not None:
						icon = ref_el.relatedwork.iconResource.image.url
					elif ref_el.relatedwork.icon is not None:
						icon = ref_el.relatedwork.icon
					else:
						icon = ''

					toc_el = dom.createElement('content:related')
					toc_el.setAttribute('label', ref_el.relatedwork.title)
					toc_el.setAttribute('creator', ref_el.relatedwork.creator)
					toc_el.setAttribute('href', ref_el.uri)
					toc_el.setAttribute('type', ref_el.relatedwork.targetMimeType)
					toc_el.setAttribute('icon', icon)
					toc_el.setAttribute('desc', ref_el.description)
					toc_el.setAttribute('section', ref_el.category)
					lesson_el.appendChild(toc_el)
					lesson_el.appendChild(dom.createTextNode(u'\n'))

	def _process_related(self, dom, els):
		for el in els:
			if el.iconResource is not None:
				icon = el.iconResource.image.url
			elif el.icon is not None:
				icon = el.icon
			else:
				icon = ''

			toc_el = dom.createElement('content:related')
			toc_el.setAttribute('label', el.title)
			toc_el.setAttribute('creator', el.creator)
			toc_el.setAttribute('href', el.uri)
			toc_el.setAttribute('type', el.targetMimeType)
			toc_el.setAttribute('icon', icon)
			toc_el.setAttribute('desc', el.description)
			dom.childNodes[0].appendChild(toc_el)
			dom.childNodes[0].appendChild(dom.createTextNode(u'\n'))

@interface.implementer(crd_interfaces.IDiscussionExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _DiscussionExtractor(object):

	def __init__(self, book=None):
		pass

	def transform( self, book ):
		lesson_els = book.document.getElementsByTagName( 'courselesson' )
		dom = book.toc.dom
		if lesson_els:
			self._process_lessons(dom, lesson_els)
			book.toc.save()

	def _process_lessons(self, dom, els):
		for el in els:
			discussion_els = el.getElementsByTagName('ntidiscussion')
			discussionref_els = el.getElementsByTagName('ntidiscussionref')
			if discussion_els or discussionref_els:
				lesson_el = None

				# Determine which topic represents the lesson
				topic_els = dom.getElementsByTagName('topic')
				for topic_el in topic_els:
					if topic_el.getAttribute('ntiid') == el.ntiid:
						lesson_el = topic_el

				for discussion_el in discussion_els:
					lesson_el = None

					# Determine which topic represents the lesson
					topic_els = dom.getElementsByTagName('topic')
					for topic_el in topic_els:
						if topic_el.getAttribute('ntiid') == el.ntiid:
							lesson_el = topic_el

					if discussion_el.iconResource is not None:
						icon = discussion_el.iconResource.image.url
					else:
						icon = ''

					toc_el = dom.createElement('object')
					toc_el.setAttribute('label', discussion_el.title)
					toc_el.setAttribute('title', discussion_el.subtitle)
					toc_el.setAttribute('ntiid', discussion_el.topic_ntiid)
					toc_el.setAttribute('mimeType', discussion_el.targetMimeType)
					toc_el.setAttribute('icon', icon)
					lesson_el.appendChild(toc_el)
					lesson_el.appendChild(dom.createTextNode(u'\n'))

				for discussionref_el in discussionref_els:
					lesson_el = None

					# Determine which topic represents the lesson
					topic_els = dom.getElementsByTagName('topic')
					for topic_el in topic_els:
						if topic_el.getAttribute('ntiid') == el.ntiid:
							lesson_el = topic_el

					if discussionref_el.idref['label'].iconResource is not None:
						icon = discussionref_el.idref['label'].iconResource.image.url
					else:
						icon = ''

					toc_el = dom.createElement('object')
					toc_el.setAttribute('label', discussionref_el.idref['label'].title)
					toc_el.setAttribute('title', discussionref_el.idref['label'].subtitle)
					toc_el.setAttribute('ntiid', discussionref_el.idref['label'].topic_ntiid)
					toc_el.setAttribute('mimeType', discussionref_el.idref['label'].targetMimeType)
					toc_el.setAttribute('icon', icon)
					lesson_el.appendChild(toc_el)
					lesson_el.appendChild(dom.createTextNode(u'\n'))

@interface.implementer(crd_interfaces.INTIVideoExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _NTIVideoExtractor(object):

	def __init__(self, book=None):
		pass

	def transform(self, book):
		lesson_els = book.document.getElementsByTagName('courselesson')
		video_els = book.document.getElementsByTagName('ntivideo')
		outpath = os.path.expanduser(book.contentLocation)
		dom = book.toc.dom
		if lesson_els or video_els:
			topic_map = self._get_topic_map(dom)
			self._process_lessons(dom, lesson_els, topic_map)
			self._process_videos(dom, video_els, outpath, topic_map)
			book.toc.save()

	def _get_topic_map(self, dom):
		result = {}
		for topic_el in dom.getElementsByTagName('topic'):
			ntiid = topic_el.getAttribute('ntiid')
			if ntiid:
				result[ntiid] = topic_el
		return result

	def _find_toc_videos(self, topic_map):
		result = collections.defaultdict(set)
		for topic_ntiid, topic_el in topic_map.items():
			for obj in topic_el.getElementsByTagName('object'):
				if obj.getAttribute('mimeType') != u'application/vnd.nextthought.ntivideo':
					continue
				ntiid = obj.getAttribute('ntiid')
				if ntiid and topic_ntiid:
					result[ntiid].add(topic_ntiid)
		return result
					
	def _process_video(self, dom, video, topic_map):
		entry = {'sources':[], 'transcripts':[]}

		entry['ntiid'] = video.ntiid
		entry['creator'] = video.creator
		if hasattr(video.title, 'textContent'):
			entry['title'] = video.title.textContent
		else:
			entry['title'] = video.title

		entry['mimeType'] = video.mimeType
		entry['description'] = video.description
		entry['closedCaptions'] = video.closed_caption

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
			entry['sources'].append(val)

		for transcript in video.getElementsByTagName('mediatranscript'):
			val = {}
			val['src'] = transcript.raw.url
			val['srcjsonp'] = transcript.wrapped.url
			val['lang'] = transcript.attributes['lang']
			val['type'] = transcript.transcript_mime_type
			val['purpose'] = transcript.attributes['purpose']
			entry['transcripts'].append(val)

		# find parent document
		parent = video.parentNode
		while parent is not None and not isinstance(parent, LaTexDocument.document):
			ntiid = getattr(parent, 'ntiid', None) or u''
			if ntiid in topic_map:
				break
			else:
				parent = parent.parentNode

		container = getattr(parent, 'ntiid', None) if parent else None
		return entry, container

	def _process_videos(self, dom, els, outpath, topic_map):
		items = {}
		filename = 'video_index.json'
		inverted = collections.defaultdict(set)
		containers = collections.defaultdict(list)
		video_index = {'Items': items, 'Containers':containers}
		for el in els:
			video, container = self._process_video(dom, el, topic_map)
			items[video['ntiid']] = video
			if container:
				containers[container].append(video['ntiid'])
				inverted[video['ntiid']].add(container)

		# Write the normal version
		with open(os.path.join(outpath, filename), "wb") as fp:
			simplejson.dump(video_index, fp, indent=4)

		# Write the JSONP version
		with open(os.path.join(outpath, filename+'p'), "wb") as fp:
			fp.write('jsonpReceiveContent(')
			simplejson.dump({'ntiid': dom.childNodes[0].getAttribute('ntiid'),
							 'Content-Type': 'application/json',
							 'Content-Encoding': 'json',
							 'content': video_index,
							 'version': '1'}, fp, indent=4)
			fp.write(');')

		toc_el = dom.createElement('reference')
		toc_el.setAttribute('href', filename)
		toc_el.setAttribute('type', 'application/vnd.nextthought.videoindex')

		dom.childNodes[0].appendChild(toc_el)
		dom.childNodes[0].appendChild(dom.createTextNode(u'\n'))
		doc_ntiid = dom.documentElement.getAttribute('ntiid')

		# add video objects to toc
		videos_in_toc = self._find_toc_videos(topic_map)
		for ntiid, containers in inverted.items():
			
			if ntiid in videos_in_toc:
				continue
			
			for container in containers:
				if container == doc_ntiid:
					parent = dom.documentElement
				else:
					parent = topic_map.get(container)
					if parent is None:
						continue

				# create new elemenet
				video = items.get(ntiid)
				obj_el = dom.createElement('object')
				label = video.get('title') if video else None
				obj_el.setAttribute(u'label', label or u'')
				obj_el.setAttribute(u'mimeType', u'application/vnd.nextthought.ntivideo')
				obj_el.setAttribute(u'ntiid', ntiid)

				# add to parent
				parent.childNodes.append(obj_el)

	def _process_lessons(self, dom, els, topic_map):
		for el in els:
			video_els = el.getElementsByTagName('ntivideoref')
			if video_els:
				lesson_el = None

				# Determine which topic represents the lesson
				lesson_el = topic_map.get(el.ntiid)

				for video_el in video_els:

					# Determine which topic represents the lesson
					lesson_el = topic_map.get(el.ntiid)

					poster = ''
					source_els = video_el.idref['label'].getElementsByTagName('ntivideosource')
					if source_els:
						poster = source_els[0].poster

					toc_el = dom.createElement('object')
					if hasattr(video_el.idref['label'].title, 'textContent'):
						toc_el.setAttribute('label', video_el.idref['label'].title.textContent)
					else:
						toc_el.setAttribute('label', video_el.idref['label'].title)
					toc_el.setAttribute('poster', poster)
					toc_el.setAttribute('ntiid', video_el.idref['label'].ntiid)
					toc_el.setAttribute('mimeType', video_el.idref['label'].mimeType)
					if lesson_el is not None:
						lesson_el.appendChild(toc_el)
						lesson_el.appendChild(dom.createTextNode(u'\n'))

@interface.implementer(crd_interfaces.IHackExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _HackExtractor(object):

	def __init__(self, book=None):
		pass

	def transform( self, book ):
		if book.jobname == 'CLC3403_LawAndJustice':
			logger.warn('Applying SUPER hack!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			hack_el = book.toc.dom.createElement('object')
			hack_el.setAttribute('label', 'Quiz 1')
			hack_el.setAttribute('mimeType', 'application/vnd.nextthought.naquestionset')
			hack_el.setAttribute('gotoNtiid', 'tag:nextthought.com,2011-10:OU-HTML-CLC3403_LawAndJustice.sec:QUIZ_01.01')
			hack_el.setAttribute('ntiid', 'tag:nextthought.com,2011-10:NTI-NAQ-CLC3403_LawAndJustice.naquestionset.questionset1')
			hack_el.setAttribute('correct', '7')
			hack_el.setAttribute('incorrect', '2')

			lesson_els = book.document.getElementsByTagName( 'courselesson' )
			if lesson_els:
				topic_els = book.toc.dom.getElementsByTagName('topic')
				for topic_el in topic_els:
					if lesson_els[0].ntiid == topic_el.getAttribute('ntiid'):
						topic_el.appendChild(hack_el)
						topic_el.appendChild(book.toc.dom.createTextNode(u'\n'))
						book.toc.save()
					elif lesson_els[1].getAttribute('target-ntiid') == topic_el.getAttribute('ntiid'):
						topic_el.appendChild(hack_el)
						topic_el.appendChild(book.toc.dom.createTextNode(u'\n'))
						book.toc.save()

