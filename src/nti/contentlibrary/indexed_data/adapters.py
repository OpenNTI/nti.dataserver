#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters to get indexed data for content units.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys

from zope import interface

from zope.annotation.interfaces import IAnnotations

from . import container
from . import interfaces

from .interfaces import TAG_NAMESPACE_FILE

_KEY =  'nti.contentlibrary.indexed_data.container.IndexedDataContainer'

def indexed_data_adapter(content_unit,
						 factory=container.IndexedDataContainer,
						 iface=interfaces.IIndexedDataContainer):
	key = _KEY
	namespace = iface.queryTaggedValue(TAG_NAMESPACE_FILE,'')
	if namespace:
		key = key + '_' + namespace

	annotations = IAnnotations(content_unit)
	result = annotations.get(key)
	if result is None:
		result = annotations[key] = factory(content_unit.ntiid)
		result.__name__ = key
		# Notice that, unlike a typical annotation factory,
		# we do not set (or check!) the result object parent
		# to be the content unit. This is because we don't want to
		# hold a reference to it because the annotations may be
		# on a different utility
	return result

def _make_adapters():
	frame = sys._getframe(1)
	__module__ = frame.f_globals['__name__']

	types = ('audio', 'video', 'related_content', 'timeline', 'slide_deck')

	def make_func(iface, factory):
		@interface.implementer(iface)
		def func(content_unit):
			return indexed_data_adapter(content_unit,
										factory=factory,
										iface=iface)
		return func

	for base in types:
		identifier = ''.join([x.capitalize() for x in base.split('_')])
		identifier = identifier + 'IndexedDataContainer'
		iface = getattr(interfaces, 'I' + identifier )
		factory = getattr(container, identifier)

		func = make_func(iface, factory)
		func_name = base + '_indexed_data_adapter'
		func.__name__ = str(func_name)
		frame.f_globals[func_name] = func

_make_adapters()
