#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Zope content providers that integrate with pyramid.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.contentprovider.provider import ContentProviderBase

from pyramid.renderers import render

class _PyramidRendererContentProvider(ContentProviderBase):
	"""
	Renders using a named Pyramid renderer.
	"""

	def __init__(self, context, request, view, name):
		super(_PyramidRendererContentProvider, self).__init__(context, request, view)
		self.__name__ = name

	def render(self, *args, **kwargs):
		return render(self.__name__,
					  None,  # value
					  request=self.request)

class PyramidRendererContentProviderFactory(object):
	"""
	A factory to register in ZCA to produce a content provider.
	"""

	def __init__(self, template_spec):
		self.template_spec = template_spec

	def __call__(self, context, request, view):
		return _PyramidRendererContentProvider(context, request, view, self.template_spec)
