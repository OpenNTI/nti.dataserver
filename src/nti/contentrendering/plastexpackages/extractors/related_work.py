#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import collections
import simplejson as json

from zope import component
from zope import interface

from plasTeX.Renderers import render_children

from ...interfaces import IRenderedBook
from ...interfaces import IRelatedWorkExtractor

def _render_children(renderer, nodes):
	return unicode(''.join(render_children(renderer, nodes)))
	
@interface.implementer(IRelatedWorkExtractor)
@component.adapter(IRenderedBook)
class _RelatedWorkExtractor(object):

	def __init__(self, book=None):
		pass
		
	def transform(self, book):
		dom = book.toc.dom
		related_els = book.document.getElementsByTagName('relatedwork')
		reference_els = book.document.getElementsByTagName('relatedworkref')
		if reference_els or related_els:
			outpath = os.path.expanduser(book.contentLocation)
			
			# cache topics
			topic_map = self._get_topic_map(dom)
			
			# add name space FIXME: This is not the right way to do that. 
			# It should be # managed automatically?
			dom.childNodes[0].setAttribute('xmlns:content',
										   "http://www.nextthought.com/toc")
			
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
		for el in els or ():
			if el.parentNode:
				# Discover the nearest topic in the toc that is a 'course' node
				lesson_el = None
				parent_el = el.parentNode
				if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
					lesson_el = topic_map.get(parent_el.ntiid)
					
				while lesson_el is None and parent_el.parentNode is not None:
					parent_el = parent_el.parentNode
					if hasattr(parent_el, 'ntiid') and parent_el.tagName.startswith('course'):
						lesson_el = topic_map.get(parent_el.ntiid)

				if el.uri == '':
					logger.warn('We have no valid URI!!! %s %s' % (el.ntiid, el.relatedwork.ntiid))

				targetMimeType = el.targetMimeType

				title = _render_children(el.relatedwork.renderer, el.relatedwork.title)
				creator = _render_children(el.relatedwork.renderer, el.relatedwork.creator)
				
				# SAJ: Have to un-HTML escape & to prevent it from being double escaped. It is likely
				# that we will have to unescape all HTML escape codes prior to the writing out of the ToC
				description = _render_children(el.renderer, el.description).replace('&amp;', '&')

				content = {
					'label': title,
					'creator': creator,
					'href': el.uri,
					'type': targetMimeType,
					'icon': el.icon,
					'desc': description,
					'section': el.category,
					'visibility': el.visibility,
					'target-ntiid': el.target_ntiid,
					'ntiid': el.ntiid
				}
				if lesson_el:
					result.append((content, lesson_el))
		return result

	def _process_related(self, dom, els):
		result = []
		for el in els or ():
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

			title = _render_children(el.renderer, el.title)
			creator = _render_children(el.renderer, el.creator)
			
			# SAJ: Have to un-HTML escape & to prevent it from being double escaped. It is likely
			# that we will have to unescape all HTML escape codes prior to the writing out of the ToC
			description = _render_children(el.renderer, el.description).replace('&amp;', '&')

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
		doc_ntiid = dom.documentElement.getAttribute('ntiid')
		related_content_index = {'Items': items, 'Containers':containers}
		
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
