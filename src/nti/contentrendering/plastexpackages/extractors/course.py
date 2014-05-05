#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
course extractors

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from plasTeX.Renderers import render_children

from nti.contentrendering import interfaces as crd_interfaces

from nti.externalization.externalization import to_external_object

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
			# TODO: These might be relative to the parent (e.g., +1 week)
			for date in lesson_dates:
				# The correct timezone information has already been taken care of
				date_strings.append( to_external_object(date ) )

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
