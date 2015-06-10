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

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from nti.contenttypes.presentation.interfaces import INTIAudio
from nti.contenttypes.presentation.interfaces import INTIVideo
from nti.contenttypes.presentation.interfaces import INTISlide
from nti.contenttypes.presentation.interfaces import INTITimeline
from nti.contenttypes.presentation.interfaces import INTISlideDeck
from nti.contenttypes.presentation.interfaces import INTISlideVideo
from nti.contenttypes.presentation.interfaces import INTIRelatedWorkRef

from . import container
from . import interfaces

_KEY =  'nti.contentlibrary.indexed_data.container.IndexedDataContainerLastModified'

from .interfaces import TAG_NAMESPACE_FILE
from .interfaces import IContainedTypeAdapter

class _Type(object):

	__slots__ = (b'type',)

	def __init__(self, type):
		self.type = type

@component.adapter( INTIAudio )
@interface.implementer(IContainedTypeAdapter)
def _audio_to_contained_type(context):
	return _Type( 'NTIAudio' )

@component.adapter( INTIVideo )
@interface.implementer(IContainedTypeAdapter)
def _video_to_contained_type(context):
	return _Type( 'NTIVideo' )

@component.adapter( INTISlide )
@interface.implementer(IContainedTypeAdapter)
def _slide_to_contained_type(context):
	return _Type( 'NTISlide' )

@component.adapter( INTITimeline )
@interface.implementer(IContainedTypeAdapter)
def _timeline_to_contained_type(context):
	return _Type( 'NTITimeline' )

@component.adapter( INTISlideDeck )
@interface.implementer(IContainedTypeAdapter)
def _slidedeck_to_contained_type(context):
	return _Type( 'NTISlideDeck' )

@component.adapter( INTISlideVideo )
@interface.implementer(IContainedTypeAdapter)
def _slidevideo_to_contained_type(context):
	return _Type( 'NTISlideVideo' )

@component.adapter( INTIRelatedWorkRef )
@interface.implementer(IContainedTypeAdapter)
def _related_to_contained_type(context):
	return _Type( 'NTIRelatedWorkRef' )

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
