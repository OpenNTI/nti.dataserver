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
from collections import OrderedDict

from plasTeX.Base.LaTeX import Document as LaTexDocument

from zope import component
from zope import interface

from nti.common.sets import OrderedSet

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
			topic_map = self._get_topic_map(dom)
			content = self._process_timelime(dom, timeline_els, topic_map)
			self._save_timeline_content(outpath, dom, content)

	def _get_topic_map(self, dom):
		result = OrderedDict()
		for topic_el in dom.getElementsByTagName('topic'):
			ntiid = topic_el.getAttribute('ntiid')
			if ntiid:
				result[ntiid] = topic_el
		return result

	def _process_timelime(self, dom, elements, topic_map):
		result = []
		for el in elements or ():
			uri = el.uri
			ntiid = el.ntiid
			title = _render_children(el.renderer, el.title)
			icon = el.icon.image.url if el.icon is not None else None
			description = _render_children(el.renderer, el.description)
			content = {
				'href': uri,
				'icon': icon,
				'label': title,
				'ntiid': ntiid,
				'desc': description,
			}
			# find parent document
			parent = el.parentNode
			while parent is not None and not isinstance(parent, LaTexDocument.document):
				ntiid = getattr(parent, 'ntiid', None) or u''
				if ntiid in topic_map:
					break
				else:
					parent = parent.parentNode

			container = getattr(parent, 'ntiid', None) if parent else None
			result.append((content, container))
		return result
	
	def _add_2_od(self, od, key, value):
		s = od.get(key)
		if s is None:
			s = od[key] = OrderedSet()
		s.add(value)
		
	def _save_timeline_content(self, outpath, dom, content_items):
		items = {}
		containers = OrderedDict()
		doc_ntiid = dom.documentElement.getAttribute('ntiid')
		related_content_index = {'Items': items, 'Containers':containers}

		for data, container in content_items:
			container = container or doc_ntiid
			if not container:
				continue

			items[data['ntiid']] = data
			self._add_2_od(containers, container, data['ntiid'])

		for ntiid, tid_ids in list(containers.items()):
			containers[ntiid] = list(tid_ids)  # Make JSON Serializable

		# Write the normal version
		filename = 'timeline_index.json'
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
