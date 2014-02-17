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
import collections
import simplejson as json  # Needed for sort_keys, ensure_ascii

from zope import component
from zope import interface

from pytz import utc as tz_utc

from plasTeX.Base.LaTeX import Document as LaTexDocument
from plasTeX.Renderers import render_children

from nti.contentrendering import interfaces as crd_interfaces

@interface.implementer(crd_interfaces.ICourseExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _CourseExtractor(object):

	def __init__(self, book=None):
		pass

	def transform(self, book):
		course_els = book.document.getElementsByTagName('course')
		courseinfo = book.document.getElementsByTagName('courseinfo')
		dom = book.toc.dom
		if course_els:
			dom.childNodes[0].appendChild(self._process_course(dom, course_els[0], courseinfo))
			dom.childNodes[0].setAttribute('isCourse', 'true')
		else:
			dom.childNodes[0].setAttribute('isCourse', 'false')
		book.toc.save()

	def _process_course(self, dom, doc_el, courseinfo):
		toc_el = dom.createElement('course')
		toc_el.setAttribute('label', ''.join(render_children( doc_el.renderer, doc_el.title)))
		toc_el.setAttribute('courseName', ''.join(render_children( doc_el.renderer, doc_el.number)))
		toc_el.setAttribute('ntiid', doc_el.ntiid)
		if hasattr(doc_el, 'discussion_board'):
			toc_el.setAttribute('discussionBoard', doc_el.discussion_board)
		if hasattr(doc_el, 'announcement_board'):
			toc_el.setAttribute('instructorForum', doc_el.announcement_board)
		if courseinfo:
			toc_el.setAttribute('courseInfo', courseinfo[0].ntiid)
		units = doc_el.getElementsByTagName('courseunit')

		# SAJ: All courses should now have a course_info.json file, so always add this node
		info = dom.createElement('info')
		info.setAttribute('src', u'course_info.json')
		toc_el.appendChild(info)
		for unit in units:
			toc_el.appendChild(self._process_unit(dom, unit))

		for node in self._process_communities(dom, doc_el):
			toc_el.appendChild(node)
		return toc_el

	def _process_unit(self, dom, doc_el):
		toc_el = dom.createElement('unit')
		toc_el.setAttribute('label', unicode(doc_el.title))
		toc_el.setAttribute('ntiid', doc_el.ntiid)
		toc_el.setAttribute('levelnum', '0')

		lesson_refs = doc_el.getElementsByTagName('courselessonref')
		course_node = doc_el
		while course_node.tagName != 'course':
			course_node = course_node.parentNode

		for lesson_ref in lesson_refs:
			lesson_ref_dates = lesson_ref.date
			lesson = lesson_ref.idref['label']

			toc_el.appendChild(self._process_lesson(dom, course_node, lesson, lesson_ref_dates, level=1))
		return toc_el

	def _process_lesson(self, dom, course_node, lesson_node, lesson_dates=None, level=1):
		date_strings = None
		if lesson_dates:
			date_strings = []
			# SAJ: Add the course's timezone and translate to UTC
			tz = course_node.tz
			# TODO: These might be relative to the parent (e.g., +1 week)

			for date in lesson_dates:
				date_strings.append(tz_utc.normalize(tz.localize(date).astimezone(tz_utc)).isoformat())

		toc_el = dom.createElement('lesson')
		if date_strings:
			toc_el.setAttribute('date', ','.join(date_strings))
		toc_el.setAttribute('topic-ntiid', lesson_node.ntiid)
		toc_el.setAttribute( 'levelnum', str(level))
		toc_el.setAttribute( 'isOutlineStubOnly', 'true' if lesson_node.is_outline_stub_only else 'false')

		for sub_lesson in lesson_node.subsections:
			if not sub_lesson.tagName.startswith('course'):
				continue
			dates = getattr(sub_lesson, 'date', None)
			child = self._process_lesson( dom, course_node, sub_lesson, dates, level=level+1)
			toc_el.appendChild( child )

		return toc_el

	def _process_communities(self, dom, doc_el):
		communities = doc_el.getElementsByTagName('coursecommunity')
		com_els = []
		public = []
		restricted = []
		for community in communities:
			entry_el = dom.createElement('entry')
			entry_el.appendChild(dom.createTextNode(community.attributes['ntiid']))
			if community.scope == 'restricted':
				restricted.append(entry_el)
			else:
				public.append(entry_el)

		if public:
			scope_el = dom.createElement('scope')
			scope_el.setAttribute('type', u'public')
			for entry in public:
				scope_el.appendChild(entry)
			com_els.append(scope_el)

		if restricted:
			scope_el = dom.createElement('scope')
			scope_el.setAttribute('type', u'restricted')
			for entry in restricted:
				scope_el.appendChild(entry)
			com_els.append(scope_el)

		return com_els

@interface.implementer(crd_interfaces.IRelatedWorkExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _RelatedWorkExtractor(object):

	def __init__(self, book=None):
		pass

	def transform( self, book ):
		dom = book.toc.dom
		reference_els = book.document.getElementsByTagName( 'relatedworkref' )
		related_els = book.document.getElementsByTagName( 'relatedwork' )
		if reference_els or related_els:
			outpath = os.path.expanduser(book.contentLocation)
			# add name space
			# FIXME: This is not the right way to do that. It should be
			# managed automatically?
			dom.childNodes[0].setAttribute('xmlns:content', "http://www.nextthought.com/toc")
			# cache topics
			topic_map = self._get_topic_map(dom)
			# get content data
			content = self._process_references(dom, reference_els, topic_map)
			content.extend(self._process_related(dom, related_els))
			# save dom and files
			self._save_related_content(outpath, dom, content)
			book.toc.save()

	def _get_topic_map(self, dom):
		result = {}
		for topic_el in dom.getElementsByTagName('topic'):
			ntiid = topic_el.getAttribute('ntiid')
			if ntiid:
				result[ntiid] = topic_el
		return result

	def _process_references(self, dom, els, topic_map):
		result = []
		for el in els:
			if el.parentNode:
				# Discover the nearest topic in the toc that is a 'course' node
				parent_el = el.parentNode
				lesson_el = None
				if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
					lesson_el = topic_map.get(parent_el.ntiid)
				while lesson_el is None and parent_el.parentNode is not None:
					parent_el = parent_el.parentNode
					if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
						lesson_el = topic_map.get(parent_el.ntiid)

				if el.relatedwork.iconResource is not None:
					icon = el.relatedwork.iconResource.image.url
				elif el.relatedwork.icon is not None:
					icon = el.relatedwork.icon
				else:
					icon = ''

				if el.description == '':
					el.description = el.relatedwork.description

				visibility = (el.visibility or el.relatedwork.visibility)

				uri = el.uri

				if uri == '':
					el.uri = el.relatedwork.uri
					el.gen_target_ntiid()
					uri = el.uri

				if uri == '':
					logger.warn('We are still empty!!!!!!!!!!!!!!!!!!!!!!!! %s %s' % (el.ntiid, el.relatedwork.ntiid))

				if uri != '' and el.target_ntiid is None:
					el.gen_target_ntiid()

				targetMimeType = el.targetMimeType

				if targetMimeType is None:
					el.relatedwork.gen_target_ntiid()
					targetMimeType = el.relatedwork.targetMimeType

				title = unicode(''.join(render_children( el.relatedwork.renderer, el.relatedwork.title )))
				creator = unicode(''.join(render_children( el.relatedwork.renderer, el.relatedwork.creator )))
				description = unicode(el.description)

				content = {
					'label': title,
					'creator': creator,
					'href': uri,
					'type': targetMimeType,
					'icon': icon,
					'desc': description,
					'section': el.category,
					'visibility': visibility,
					'target-ntiid': el.target_ntiid,
					'ntiid': el.ntiid
				}
				if lesson_el:
					result.append((content, lesson_el))
		return result

	def _process_related(self, dom, els):
		result = []
		for el in els:
			if el.iconResource is not None:
				icon = el.iconResource.image.url
			elif el.icon is not None:
				icon = el.icon
			else:
				icon = ''

			uri = el.uri

			if uri == '':
				logger.warn('No URI specified for %s' % el.ntiid)

			if uri != '' and el.targetMimeType is None:
				el.gen_target_ntiid()

			title = unicode(''.join(render_children( el.renderer, el.title )))
			creator = unicode(''.join(render_children( el.renderer, el.creator )))
			description = unicode( el.description )

			content = {
				'label': title,
				'creator': creator,
				'href': uri,
				'type': el.targetMimeType,
				'icon': icon,
				'desc': description,
				'visibility': el.visibility,
				'target-ntiid': el.target_ntiid,
				'ntiid': el.ntiid
			}
			result.append((content, dom.childNodes[0]))
		return result

	def _save_related_content(self, outpath, dom, content_items):
		items = {}
		filename = 'related_content_index.json'
		containers = collections.defaultdict(set)
		related_content_index = {'Items': items, 'Containers':containers}
		doc_ntiid = dom.documentElement.getAttribute('ntiid')

		for d, node in content_items:
			if node is None:
				continue
			el = dom.createElementNS("http://www.nextthought.com/toc", 'content:related')
			for name, value in d.items():
				el.setAttribute(unicode(name), unicode(value))
			node.appendChild(el)

			items[d['ntiid']] = d
			container = node.getAttribute('ntiid') or doc_ntiid
			containers[container].add(d['ntiid'])

		for ntiid, vid_ids in list(containers.items()):
			containers[ntiid] = list(vid_ids)  # Make JSON Serializable

		# Write the normal version
		with open(os.path.join(outpath, filename), "wb") as fp:
			json.dump(related_content_index, fp, indent=4)

		# Write the JSONP version
		with open(os.path.join(outpath, filename + 'p'), "wb") as fp:
			fp.write('jsonpReceiveContent(')
			json.dump({'ntiid': dom.childNodes[0].getAttribute('ntiid'),
					   'Content-Type': 'application/json',
					   'Content-Encoding': 'json',
					   'content': related_content_index,
					   'version': '1'}, fp, indent=4)
			fp.write(');')

@interface.implementer(crd_interfaces.IDiscussionExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _DiscussionExtractor(object):

	def __init__(self, book=None):
		pass

	def transform( self, book ):
		lesson_els = book.document.getElementsByTagName( 'courselesson' )
		dom = book.toc.dom
		if lesson_els:
			topic_map = self._get_topic_map(dom)
			self._process_lessons(dom, lesson_els, topic_map)
			book.toc.save()

	def _get_topic_map(self, dom):
		result = {}
		for topic_el in dom.getElementsByTagName('topic'):
			ntiid = topic_el.getAttribute('ntiid')
			if ntiid:
				result[ntiid] = topic_el
		return result

	def _process_lessons(self, dom, els, topic_map):
		for el in els:
			discussion_els = el.getElementsByTagName('ntidiscussion')
			discussionref_els = el.getElementsByTagName('ntidiscussionref')
			if discussion_els or discussionref_els:
				for discussion_el in discussion_els:
					# Discover the nearest topic in the toc that is a 'course' node
					parent_el = discussion_el.parentNode
					lesson_el = None
					if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
						lesson_el = topic_map.get(parent_el.ntiid)
					while lesson_el is None and parent_el.parentNode is not None:
						parent_el = parent_el.parentNode
						if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
							lesson_el = topic_map.get(parent_el.ntiid)

					if discussion_el.iconResource is not None:
						icon = discussion_el.iconResource.image.url
					else:
						icon = ''

					title = unicode(''.join(render_children( discussion_el.renderer, discussion_el.title )))
					subtitle = unicode(''.join(render_children( discussion_el.renderer, discussion_el.subtitle )))

					toc_el = dom.createElement('object')
					toc_el.setAttribute('label', title)
					toc_el.setAttribute('title', subtitle)
					toc_el.setAttribute('ntiid', discussion_el.topic_ntiid)
					toc_el.setAttribute('mimeType', discussion_el.targetMimeType)
					toc_el.setAttribute('icon', icon)
					if lesson_el:
						lesson_el.appendChild(toc_el)

				for discussionref_el in discussionref_els:
					# Discover the nearest topic in the toc that is a 'course' node
					parent_el = discussionref_el.parentNode
					lesson_el = None
					if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
						lesson_el = topic_map.get(parent_el.ntiid)
					while lesson_el is None and parent_el.parentNode is not None:
						parent_el = parent_el.parentNode
						if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
							lesson_el = topic_map.get(parent_el.ntiid)

					if discussionref_el.idref['label'].iconResource is not None:
						icon = discussionref_el.idref['label'].iconResource.image.url
					else:
						icon = ''

					title = unicode(''.join(render_children( discussionref_el.idref['label'].renderer, discussionref_el.idref['label'].title )))
					subtitle = unicode(''.join(render_children( discussionref_el.idref['label'].renderer, discussionref_el.idref['label'].subtitle )))

					toc_el = dom.createElement('object')
					toc_el.setAttribute('label', title)
					toc_el.setAttribute('title', subtitle)
					toc_el.setAttribute('ntiid', discussionref_el.idref['label'].topic_ntiid)
					toc_el.setAttribute('mimeType', discussionref_el.idref['label'].targetMimeType)
					toc_el.setAttribute('icon', icon)
					if lesson_el:
						lesson_el.appendChild(toc_el)

@interface.implementer(crd_interfaces.INTIVideoExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _NTIVideoExtractor(object):

	def __init__(self, book=None):
		pass

	def transform(self, book):
		reference_els = book.document.getElementsByTagName('ntivideoref')
		video_els = book.document.getElementsByTagName('ntivideo')
		outpath = os.path.expanduser(book.contentLocation)
		dom = book.toc.dom
		if reference_els or video_els:
			topic_map = self._get_topic_map(dom)
			self._process_references(dom, reference_els, topic_map)
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
		# We'd like these things, especially Containers, to be
		# ordered as they are in the source. We can preserve it here,
		# if we try. The original list of elements must be in order
		# of how they appear in the source, and it is more-or-less.

		# In practice, it's not nearly that simple because of the
		# "overrides". In practice, all ntivideo elements are children
		# of the document for some reason, and ntivideoref elements
		# are scattered about through the content to refer to these
		# elements. In turn, these ntivideoref elements get added to
		# the ToC dom (NOT the content dom) as "<object>" tags...we go
		# through and "re-parent" ntivideo elements in the Containers
		# collection based on where references appear to them

		# Therefore, we maintain yet another parallel data structure
		# recording the original iteration order of the elements,
		# and at the very end, when we have assigned videos
		# to containers, we sort that list by this original order.

		inverted = collections.defaultdict(set)
		containers = collections.defaultdict(set)
		video_index = {'Items': items, 'Containers':containers}
		original_video_iteration_order = []

		for el in els:
			video, container = self._process_video(dom, el, topic_map)
			items[video['ntiid']] = video
			original_video_iteration_order.append(video['ntiid'])
			if container:
				containers[container].add(video['ntiid'])
				inverted[video['ntiid']].add(container)

		# add video objects to toc and compute re-parent locations
		# based on references
		doc_ntiid = dom.documentElement.getAttribute('ntiid')
		overrides = collections.defaultdict(set)
		videos_in_toc = self._find_toc_videos(topic_map)
		for vid_ntiid, cnt_ids in inverted.items():
			toc_entries = videos_in_toc.get(vid_ntiid)
			if toc_entries:
				for toc_container_id in toc_entries:
					overrides[vid_ntiid].add(toc_container_id)
			else:
				for container in cnt_ids:
					if container == doc_ntiid:
						parent = dom.documentElement
					else:
						parent = topic_map.get(container)
						if parent is None:
							continue

					# create new elemenet
					video = items.get(vid_ntiid)
					obj_el = dom.createElement('object')
					label = video.get('title') if video else None
					obj_el.setAttribute(u'label', label or u'')
					obj_el.setAttribute(u'mimeType', u'application/vnd.nextthought.ntivideo')
					obj_el.setAttribute(u'ntiid', vid_ntiid)

					# add to parent
					parent.childNodes.append(obj_el)

		# apply overrides
		# remove from all existing. TOC always win
		for vid_ntiid in overrides.keys():
			for container in containers.values():
				container.discard(vid_ntiid)

		for vid_ntiid, cnt_ids in overrides.items():
			for container in cnt_ids:
				containers[container].add(vid_ntiid)

		# remove any empty elements
		for ntiid, vid_ids in list(containers.items()):
			if not vid_ids:
				containers.pop(ntiid)
			else:
				# Make JSON Serializable (a plain list object),
				# and also sort according to original iteration order.
				# This is easily done as a selection sort:
				# iterate across the videos in the original order, and if
				# it is included in our set, output it
				containers[ntiid] = [orig_video_id
									 for orig_video_id
									 in original_video_iteration_order
									 if orig_video_id in vid_ids]

		# Write the normal version
		with open(os.path.join(outpath, filename), "wb") as fp:
			json.dump(video_index, fp, indent=4)

		# Write the JSONP version
		with open(os.path.join(outpath, filename+'p'), "wb") as fp:
			fp.write('jsonpReceiveContent(')
			json.dump({'ntiid': dom.childNodes[0].getAttribute('ntiid'),
					   'Content-Type': 'application/json',
					   'Content-Encoding': 'json',
					   'content': video_index,
					   'version': '1'}, fp, indent=4)
			fp.write(');')

		toc_el = dom.createElement('reference')
		toc_el.setAttribute('href', filename)
		toc_el.setAttribute('type', 'application/vnd.nextthought.videoindex')

		dom.childNodes[0].appendChild(toc_el)


	def _process_references(self, dom, els, topic_map):
		for el in els:
			if el.parentNode:
				# Discover the nearest topic in the toc that is a 'course' node
				parent_el = el.parentNode
				lesson_el = None
				if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
					lesson_el = topic_map.get(parent_el.ntiid)
				while lesson_el is None and parent_el.parentNode is not None:
					parent_el = parent_el.parentNode
					if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
						lesson_el = topic_map.get(parent_el.ntiid)

				poster = ''
				source_els = el.idref['label'].getElementsByTagName('ntivideosource')
				if source_els:
					poster = source_els[0].poster

				visibility = (el.visibility or el.idref['label'].visibility)

				toc_el = dom.createElement('object')
				if hasattr(el.idref['label'].title, 'textContent'):
					toc_el.setAttribute('label', el.idref['label'].title.textContent)
				else:
					toc_el.setAttribute('label', el.idref['label'].title)
				toc_el.setAttribute('poster', poster)
				toc_el.setAttribute('ntiid', el.idref['label'].ntiid)
				toc_el.setAttribute('mimeType', el.idref['label'].mimeType)
				toc_el.setAttribute('visibility', visibility)
				if lesson_el is not None:
					lesson_el.appendChild(toc_el)
