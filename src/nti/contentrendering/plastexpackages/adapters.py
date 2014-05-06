# -*- coding: utf-8 -*-
"""
adapters for externalizing plasTeX objects

.. $Id: $
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from plasTeX.Renderers import render_children

from nti.contentrendering import interfaces as crd_interfaces


@interface.implementer(crd_interfaces.IJSONTransformer)
class _RelatedWorkRefJSONTransformer(object):

	def __init__(self, element):
		self.el = element

	def transform(self):
		output = {}
		output['creator'] = unicode(''.join(render_children( self.el.relatedwork.renderer, self.el.relatedwork.creator ))).strip()
		output['desc'] = unicode(''.join(render_children( self.el.relatedwork.renderer, self.el.relatedwork.description ))).strip()
		output['href'] = self.el.uri
		output['MimeType'] = self.el.mimeType
		output['targetMimeType'] = self.el.targetMimeType
		output['icon'] = self.el.relatedwork.iconResource.image.url
		output['label'] = unicode(''.join(render_children( self.el.relatedwork.renderer, self.el.relatedwork.title ))).strip()
		output['NTIID'] = self.el.ntiid
		output['target-NTIID'] = self.el.target_ntiid
		output['section'] = self.el.category
		output['visibility'] = self.el.visibility
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


