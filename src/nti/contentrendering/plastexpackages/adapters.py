# -*- coding: utf-8 -*-
"""
adapters for externalizing plasTeX objects

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import interface

from plasTeX.Renderers import render_children

from ..interfaces import IJSONTransformer

def _render_children(renderer, nodes, strip=True):
	if not isinstance(nodes, six.string_types):
		result = unicode(''.join(render_children(renderer, nodes)))
	else:
		result = nodes.decode("utf-8") if isinstance(nodes, bytes) else nodes
	return result.strip() if result and strip else result

@interface.implementer(IJSONTransformer)
class _CourseLessonJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['NTIID'] = self.el.ntiid
		output['MimeType'] = u"application/vnd.nextthought.ntilessonoverview"
		output['title'] = _render_children(self.el.renderer, self.el.title, False)
		output['Items'] = items = []
		group_els = self.el.getElementsByTagName('courseoverviewgroup')
		for group_el in group_els:
			trx = IJSONTransformer(group_el, None)
			if trx is not None:
				items.append(trx.transform())
		return output

@interface.implementer(IJSONTransformer)
class _CourseOverviewGroupJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['MimeType'] =  self.el.mime_type
		output['title'] = _render_children(self.el.renderer, self.el.title, False)
		output['accentColor'] = _render_children(self.el.renderer, self.el.title_background_color, False)
		output['Items'] = items = []
		for child in self.el.childNodes:
			trx = IJSONTransformer(child, None)
			if trx is not None:
				items.append(trx.transform())
		return output

@interface.implementer(IJSONTransformer)
class _CourseOverviewSpacerJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['MimeType'] =  self.el.mime_type
		return output

@interface.implementer(IJSONTransformer)
class _DiscussionRefJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['MimeType'] = self.el.discussion.targetMimeType
		output['icon'] = self.el.discussion.iconResource.image.url
		output['label'] = _render_children(self.el.discussion.renderer, self.el.discussion.title)
		output['NTIID'] = self.el.discussion.topic_ntiid
		output['title'] = _render_children(self.el.discussion.renderer, self.el.discussion.subtitle)
		return output


@interface.implementer(IJSONTransformer)
class _NTIAudioRefJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['label'] = _render_children(self.el.media.renderer, self.el.media.title)
		output['MimeType'] = self.el.media.mimeType
		output['NTIID'] = self.el.media.ntiid
		output['visibility'] = self.el.visibility
		return output

@interface.implementer(IJSONTransformer)
class _NTIVideoRefJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['label'] = _render_children(self.el.media.renderer, self.el.media.title)
		output['MimeType'] = self.el.media.mimeType
		output['NTIID'] = self.el.media.ntiid
		output['poster'] = self.el.media.poster
		output['visibility'] = self.el.visibility
		return output

@interface.implementer(IJSONTransformer)
class _RelatedWorkRefJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['creator'] = _render_children(self.el.relatedwork.renderer, self.el.creator)
		output['desc'] = _render_children( self.el.relatedwork.renderer, self.el.description)
		output['href'] = self.el.uri
		output['MimeType'] = self.el.mimeType
		output['targetMimeType'] = self.el.targetMimeType
		output['icon'] = self.el.relatedwork.iconResource.image.url
		output['label'] = _render_children(self.el.relatedwork.renderer, self.el.title)
		output['NTIID'] = self.el.ntiid
		output['target-NTIID'] = self.el.target_ntiid
		output['section'] = self.el.category
		output['visibility'] = self.el.visibility
		return output

@interface.implementer(IJSONTransformer)
class _TimelineJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['desc'] = _render_children( self.el.renderer, self.el.description)
		output['href'] = self.el.uri
		output['MimeType'] = self.el.mime_type
		output['icon'] = self.el.icon.image.url
		output['label'] = _render_children(self.el.renderer, self.el.title)
		output['NTIID'] = self.el.ntiid
		output['suggested-inline'] = self.el.suggested_inline
		if self.el.suggested_height:
			output['suggested-height'] = self.el.suggested_height
		if self.el.suggested_width:
			output['suggested-width'] = self.el.suggested_width
		return output

