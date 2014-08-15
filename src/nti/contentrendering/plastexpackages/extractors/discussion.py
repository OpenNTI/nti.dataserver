#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from plasTeX.Renderers import render_children

from ...interfaces import IRenderedBook
from ...interfaces import IDiscussionExtractor

def _render_children(renderer, nodes):
	return unicode(''.join(render_children(renderer, nodes)))

@interface.implementer(IDiscussionExtractor)
@component.adapter(IRenderedBook)
class _DiscussionExtractor(object):

	def __init__(self, book=None):
		pass

	def transform(self, book):
		lesson_els = book.document.getElementsByTagName('courselesson')
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
		for el in els or ():
			discussion_els = el.getElementsByTagName('ntidiscussion')
			for discussion_el in discussion_els or ():
				# Discover the nearest topic in the toc that is a 'course' node
				lesson_el = None
				parent_el = discussion_el.parentNode
				if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
					lesson_el = topic_map.get(parent_el.ntiid)

				while lesson_el is None and parent_el.parentNode is not None:
					parent_el = parent_el.parentNode
					if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
						lesson_el = topic_map.get(parent_el.ntiid)

				icon = 	discussion_el.iconResource.image.url \
						if discussion_el.iconResource is not None else ''
				
				title = _render_children(discussion_el.renderer, discussion_el.title)
				subtitle = _render_children(discussion_el.renderer, discussion_el.subtitle)

				toc_el = dom.createElement('object')
				toc_el.setAttribute('label', title)
				toc_el.setAttribute('title', subtitle)
				toc_el.setAttribute('ntiid', discussion_el.topic_ntiid)
				toc_el.setAttribute('mimeType', discussion_el.targetMimeType)
				toc_el.setAttribute('icon', icon)
				if lesson_el:
					lesson_el.appendChild(toc_el)

			discussionref_els = el.getElementsByTagName('ntidiscussionref')
			for discussionref_el in discussionref_els or ():
				# Discover the nearest topic in the toc that is a 'course' node
				lesson_el = None
				parent_el = discussionref_el.parentNode
				if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
					lesson_el = topic_map.get(parent_el.ntiid)
					
				while lesson_el is None and parent_el.parentNode is not None:
					parent_el = parent_el.parentNode
					if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
						lesson_el = topic_map.get(parent_el.ntiid)

				icon = 	discussionref_el.discussion.iconResource.image.url \
						if discussionref_el.discussion.iconResource is not None else u''
				
				title = _render_children(discussionref_el.discussion.renderer,
										 discussionref_el.discussion.title)
				
				subtitle = _render_children(discussionref_el.discussion.renderer, 
											discussionref_el.discussion.subtitle)

				toc_el = dom.createElement('object')
				toc_el.setAttribute('label', title)
				toc_el.setAttribute('title', subtitle)
				toc_el.setAttribute('ntiid', discussionref_el.discussion.topic_ntiid)
				toc_el.setAttribute('mimeType', discussionref_el.discussion.targetMimeType)
				toc_el.setAttribute('icon', icon)
				if lesson_el:
					lesson_el.appendChild(toc_el)
