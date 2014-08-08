# -*- coding: utf-8 -*-
"""
adapters for externalizing plasTeX objects

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from plasTeX.Renderers import render_children

from nti.contentrendering import interfaces as crd_interfaces

@interface.implementer(crd_interfaces.IJSONTransformer)
class _CourseLessonJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['NTIID'] = self.el.ntiid
		output['MimeType'] = "application/vnd.nextthought.ntilessonoverview"
		output['title'] = unicode(''.join(render_children( self.el.renderer, self.el.title )))
		output['Items'] = items = []
		group_els = self.el.getElementsByTagName('courseoverviewgroup')
		for group_el in group_els:
			trx = crd_interfaces.IJSONTransformer(group_el, None)
			if trx is not None:
				items.append(trx.transform())
		return output

@interface.implementer(crd_interfaces.IJSONTransformer)
class _CourseOverviewGroupJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['MimeType'] =  self.el.mime_type
		output['title'] = unicode(''.join(render_children( self.el.renderer, self.el.title )))
		output['accentColor'] = unicode(''.join(render_children( self.el.renderer, self.el.title_background_color )))
		output['Items'] = items = []
		for child in self.el.childNodes:
			trx = crd_interfaces.IJSONTransformer(child, None)
			if trx is not None:
				items.append(trx.transform())
		return output

@interface.implementer(crd_interfaces.IJSONTransformer)
class _CourseOverviewSpacerJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['MimeType'] =  self.el.mime_type
		return output

@interface.implementer(crd_interfaces.IJSONTransformer)
class _DiscussionRefJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['MimeType'] = self.el.discussion.targetMimeType
		output['icon'] = self.el.discussion.iconResource.image.url
		output['label'] = unicode(''.join(render_children( self.el.discussion.renderer, self.el.discussion.title ))).strip()
		output['NTIID'] = self.el.discussion.topic_ntiid
		output['title'] = unicode(''.join(render_children( self.el.discussion.renderer, self.el.discussion.subtitle ))).strip()
		return output


@interface.implementer(crd_interfaces.IJSONTransformer)
class _NTIAudioRefJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['label'] = unicode(''.join(render_children( self.el.media.renderer, self.el.media.title ))).strip()
		output['MimeType'] = self.el.media.mimeType
		output['NTIID'] = self.el.media.ntiid
		output['visibility'] = self.el.visibility
		return output

@interface.implementer(crd_interfaces.IJSONTransformer)
class _NTIVideoRefJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['label'] = unicode(''.join(render_children( self.el.media.renderer, self.el.media.title ))).strip()
		output['MimeType'] = self.el.media.mimeType
		output['NTIID'] = self.el.media.ntiid
		output['poster'] = self.el.media.poster
		output['visibility'] = self.el.visibility
		return output

@interface.implementer(crd_interfaces.IJSONTransformer)
class _RelatedWorkRefJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['creator'] = unicode(''.join(render_children( self.el.relatedwork.renderer, self.el.creator ))).strip()
		output['desc'] = unicode(''.join(render_children( self.el.relatedwork.renderer, self.el.description ))).strip()
		output['href'] = self.el.uri
		output['MimeType'] = self.el.mimeType
		output['targetMimeType'] = self.el.targetMimeType
		output['icon'] = self.el.relatedwork.iconResource.image.url
		output['label'] = unicode(''.join(render_children( self.el.relatedwork.renderer, self.el.title ))).strip()
		output['NTIID'] = self.el.ntiid
		output['target-NTIID'] = self.el.target_ntiid
		output['section'] = self.el.category
		output['visibility'] = self.el.visibility
		return output

