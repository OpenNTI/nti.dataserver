#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters to get indexed data for content units.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.contenttypes.presentation.interfaces import INTIAudio
from nti.contenttypes.presentation.interfaces import INTIVideo
from nti.contenttypes.presentation.interfaces import INTISlide
from nti.contenttypes.presentation.interfaces import INTITimeline
from nti.contenttypes.presentation.interfaces import INTISlideDeck
from nti.contenttypes.presentation.interfaces import INTISlideVideo
from nti.contenttypes.presentation.interfaces import INTIRelatedWorkRef

from .interfaces import IContainedTypeAdapter

class _Type(object):

	__slots__ = (b'type',)

	def __init__(self, types):
		self.type = types

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

