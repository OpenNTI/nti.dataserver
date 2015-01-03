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

from ._utils import _render_children

from ...interfaces import IRenderedBook
from ...interfaces import ITimelineExtractor
	
@component.adapter(IRenderedBook)
@interface.implementer(ITimelineExtractor)
class _TimelineExtractor(object):

	def __init__(self, *args, **kwargs):
		pass
		
	def transform(self, book, savetoc=True, outpath=None):
		dom = book.toc.dom
		outpath = outpath or book.contentLocation
		outpath = os.path.expanduser(outpath)
		
		timeline_els = book.document.getElementsByTagName('ntitimeline')
		if timeline_els:
			outpath = os.path.expanduser(book.contentLocation)
			content = self._process_timelime(dom, timeline_els)
			self._save_timeline_content(outpath, dom, content)

	def _process_timelime(self, dom, elements=()):
		pass
# 		result = []
# 		for el in elements or ():
# 			if el.iconResource is not None:
# 				icon = el.iconResource.image.url
# 			elif el.icon is not None:
# 				icon = el.icon
# 			else:
# 				icon = ''
# 
# 			uri = el.uri
# 
# 			if uri == '':
# 				logger.warn('No URI specified for %s' % el.ntiid)
# 
# 			if uri != '' and el.targetMimeType is None:
# 				el.gen_target_ntiid()
# 
# 			title = _render_children(el.renderer, el.title)
# 			creator = _render_children(el.renderer, el.creator)
# 			
# 			# SAJ: Have to un-HTML escape & to prevent it from being double escaped. It is likely
# 			# that we will have to unescape all HTML escape codes prior to the writing out of the ToC
# 			description = _render_children(el.renderer, el.description).replace('&amp;', '&')
# 
# 			content = {
# 				'label': title,
# 				'creator': creator,
# 				'href': uri,
# 				'type': el.targetMimeType,
# 				'icon': icon,
# 				'desc': description,
# 				'visibility': el.visibility,
# 				'target-ntiid': el.target_ntiid,
# 				'ntiid': el.ntiid
# 			}
# 			result.append((content, dom.childNodes[0]))
# 		return result

	def _save_timeline_content(self, outpath, dom, content_items):
		return
# 		items = {}
# 		filename = 'related_content_index.json'
# 		containers = collections.defaultdict(set)
# 		doc_ntiid = dom.documentElement.getAttribute('ntiid')
# 		related_content_index = {'Items': items, 'Containers':containers}
# 		
# 		for d, node in content_items:
# 			if node is None:
# 				continue
# 
# 			el = dom.createElementNS("http://www.nextthought.com/toc", 'content:related')
# 			for name, value in d.items():
# 				el.setAttribute(unicode(name), unicode(value))
# 			node.appendChild(el)
# 
# 			items[d['ntiid']] = d
# 			container = node.getAttribute('ntiid') or doc_ntiid
# 			containers[container].add(d['ntiid'])
# 
# 		for ntiid, vid_ids in list(containers.items()):
# 			containers[ntiid] = list(vid_ids)  # Make JSON Serializable
# 
# 		# Write the normal version
# 		with open(os.path.join(outpath, filename), "wb") as fp:
# 			json.dump(related_content_index, fp, indent=4)
# 
# 		# Write the JSONP version
# 		with open(os.path.join(outpath, filename + 'p'), "wb") as fp:
# 			fp.write('jsonpReceiveContent(')
# 			json.dump({'ntiid': dom.childNodes[0].getAttribute('ntiid'),
# 					   'Content-Type': 'application/json',
# 					   'Content-Encoding': 'json',
# 					   'content': related_content_index,
# 					   'version': '1'}, fp, indent=4)
# 			fp.write(');')
