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
import codecs
import collections
import simplejson as json  # Needed for sort_keys, ensure_ascii

from xml.dom.minidom import Document as XMLDocument

from zope import component
from zope import interface

from pytz import utc as tz_utc

from plasTeX.Base.LaTeX import Document as LaTexDocument

from nti.contentrendering import interfaces as crd_interfaces

from nti.externalization import internalization
from nti.externalization.externalization import toExternalObject

@interface.implementer(crd_interfaces.IAssessmentExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _AssessmentExtractor(object):
	"""
	"Transforms" a rendered book by extracting assessment information into a separate file
	called ``assessment_index.json.`` This file describes a dictionary with the following
	structure::

		Items => { # Keyed by NTIID of the file
			NTIID => string # This level is about an NTIID section
			filename => string # The relative containing file for this NTIID
			AssessmentItems => { # Keyed by NTIID of the question
				NTIID => string # The NTIID of the question
				... # All the rest of the keys of the question object
			}
			Items => { # Keyed by NTIIDs of child sections; recurses
				# As containing, except 'filename' will be null/None
			}
		}

	"""

	def __init__(self, book=None):
		# Usable as either a utility factory or an adapter
		pass

	def transform(self, book):
		index = {'Items': {}}
		self._build_index(book.document.getElementsByTagName('document')[0], index['Items'])
		# index['filename'] = index.get( 'filename', 'index.html' ) # This leads to duplicate data
		index['href'] = index.get('href', 'index.html')
		with codecs.open(os.path.join(book.contentLocation, 'assessment_index.json'), 'w', encoding='utf-8') as fp:
			# sort_keys for repeatability. Do force ensure_ascii because even though we're using codes to
			# encode automatically, the reader might not decode
			json.dump(index, fp, indent='\t', sort_keys=True, ensure_ascii=True)
		return index

	def _build_index(self, element, index):
		"""
		Recurse through the element adding assessment objects to the index,
		keyed off of NTIIDs.

		:param dict index: The containing index node. Typically, this will be
			an ``Items`` dictionary in a containing index.
		"""
		if self._is_uninteresting(element):
			# It's important to identify uninteresting nodes because
			# some uninteresting nodes that would never make it into the TOC or otherwise be noticed
			# actually can present with hard-coded duplicate NTIIDs, which would
			# cause us to fail.
			return

		ntiid = getattr(element, 'ntiid', None)
		if not ntiid:
			# If we hit something without an ntiid, it's not a section-level
			# element, it's a paragraph or something like it. Thus we collapse into
			# the parent. Obviously, we'll only look for AssessmentObjects inside of here
			element_index = index
		else:
			assert ntiid not in index, ("NTIIDs must be unique", ntiid, index.keys())
			element_index = index[ntiid] = {}

			element_index['NTIID'] = ntiid
			element_index['filename'] = getattr(element, 'filename', None)
			if not element_index['filename'] and getattr(element, 'filenameoverride', None):
				# FIXME: XXX: We are assuming the filename extension. Why aren't we finding
				# these at filename? See EclipseHelp.zpts for comparison
				element_index['filename'] = getattr(element, 'filenameoverride') + '.html'
			element_index['href'] = getattr(element, 'url', element_index['filename'])

		assessment_objects = element_index.setdefault('AssessmentItems', {})

		for child in element.childNodes:
			ass_obj = getattr(child, 'assessment_object', None)
			if callable(ass_obj):
				int_obj = ass_obj()
				self._ensure_roundtrips(int_obj, provenance=child)  # Verify that we can round-trip this object
				assessment_objects[child.ntiid] = toExternalObject(int_obj)
				# assessment_objects are leafs, never have children to worry about
			elif child.hasChildNodes():  # Recurse for children if needed
				if getattr(child, 'ntiid', None):
					containing_index = element_index.setdefault('Items', {})  # we have a child with an NTIID; make sure we have a container for it
				else:
					containing_index = element_index  # an unnamed thing; wrap it up with us; should only have AssessmentItems
				self._build_index(child, containing_index)

	def _ensure_roundtrips(self, assm_obj, provenance=None):
		ext_obj = toExternalObject(assm_obj)  # No need to go into its children, like parts.
		__traceback_info__ = provenance, assm_obj, ext_obj
		raw_int_obj = type(assm_obj)()  # Use the class of the object returned as a factory.
		internalization.update_from_external_object(raw_int_obj, ext_obj, require_updater=True)
		factory = internalization.find_factory_for(toExternalObject(assm_obj))  # Also be sure factories can be found
		assert factory is not None
		# The ext_obj was mutated by the internalization process, so we need to externalize
		# again. Or run a deep copy (?)

	def _is_uninteresting(self, element):
		"""
		Uninteresting elements do not get an entry in the index. These are
		elements that have no children and no assessment items of their own.
		"""

		cache_attr = '@assessment_extractor_uninteresting'
		if getattr(element, cache_attr, None) is not None:
			return getattr(element, cache_attr)

		boring = False
		if callable(getattr(element, 'assessment_object', None)):
			boring = False
		elif not element.hasChildNodes():
			boring = True
		elif all((self._is_uninteresting(x) for x in element.childNodes)):
			boring = True

		try:
			setattr(element, cache_attr, boring)
		except AttributeError: pass

		return boring

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
			dom.childNodes[0].appendChild(dom.createTextNode(u'	'))
			dom.childNodes[0].appendChild(self._process_course(course_els[0], courseinfo))
			dom.childNodes[0].appendChild(dom.createTextNode(u'\n'))
			dom.childNodes[0].setAttribute('isCourse', 'true')
		else:
			dom.childNodes[0].setAttribute('isCourse', 'false')
		book.toc.save()

	def _process_course(self, doc_el, courseinfo):
		toc_el = XMLDocument().createElement('course')
		toc_el.setAttribute('label', unicode(doc_el.title))
		toc_el.setAttribute('ntiid', doc_el.ntiid)
		if hasattr(doc_el, 'discussion_board'):
			toc_el.setAttribute('discussionBoard', doc_el.discussion_board)
		if hasattr(doc_el, 'announcement_board'):
			toc_el.setAttribute('instructorForum', doc_el.announcement_board)
		if courseinfo:
			toc_el.setAttribute('courseInfo', courseinfo[0].ntiid)
		units = doc_el.getElementsByTagName('courseunit')
		for unit in units:
			toc_el.appendChild(XMLDocument().createTextNode(u'\n		'))
			toc_el.appendChild(self._process_unit(unit))
		toc_el.appendChild(XMLDocument().createTextNode(u'\n	'))
		return toc_el

	def _process_unit(self, doc_el):
		toc_el = XMLDocument().createElement('unit')
		toc_el.setAttribute('label', unicode(doc_el.title))
		toc_el.setAttribute('ntiid', doc_el.ntiid)
		lessons = doc_el.getElementsByTagName('courselessonref')
		for lesson in lessons:
			toc_el.appendChild(XMLDocument().createTextNode(u'\n			'))
			toc_el.appendChild(self._process_lesson(lesson))
		toc_el.appendChild(XMLDocument().createTextNode(u'\n		'))
		return toc_el

	def _process_lesson(self, doc_el):
		# SAJ: Lets find our parent course node
		course = doc_el.parentNode
		while (course.tagName != 'course'):
			course = course.parentNode

		# SAJ: Add the course's timezone and translate to UTC
		tz = course.tz
		doc_el.date = tz_utc.normalize(tz.localize(doc_el.date).astimezone(tz_utc))

		toc_el = XMLDocument().createElement('lesson')
		toc_el.setAttribute('date', doc_el.date.isoformat())
		toc_el.setAttribute('topic-ntiid', doc_el.idref['label'].ntiid)
		return toc_el

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
			topic_map = self._get_topic_map(dom)
			self._process_lessons(dom, lesson_els, topic_map)
			self._process_related(dom, related_els)
			dom.childNodes[0].setAttribute('xmlns:content', "http://www.nextthought.com/toc")
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
			ref_els = el.getElementsByTagName('relatedworkref')
			if ref_els:
				lesson_el = topic_map.get(el.ntiid)

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
					if lesson_el:
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
					lesson_el = topic_map.get(el.ntiid)

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
					if lesson_el:
						lesson_el.appendChild(toc_el)
						lesson_el.appendChild(dom.createTextNode(u'\n'))

				for discussionref_el in discussionref_els:
					lesson_el = topic_map.get(el.ntiid)

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
					if lesson_el:
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
		containers = collections.defaultdict(set)
		video_index = {'Items': items, 'Containers':containers}
		for el in els:
			video, container = self._process_video(dom, el, topic_map)
			items[video['ntiid']] = video
			if container:
				containers[container].add(video['ntiid'])
				inverted[video['ntiid']].add(container)

		# add video objects to toc
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
				containers[ntiid] = list(vid_ids)  # Make JSON Serializable

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
		dom.childNodes[0].appendChild(dom.createTextNode(u'\n'))


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
