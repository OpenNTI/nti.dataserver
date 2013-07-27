#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of media types.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.container import contained as zcontained

from nti.dataserver import interfaces as nti_interfaces

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from .base import UserContentRoot
from .threadable import ThreadableMixin
from .base import UserContentRootInternalObjectIO

@interface.implementer(nti_interfaces.IMedia, nti_interfaces.IZContained)
class Media(ThreadableMixin, UserContentRoot, zcontained.Contained, SchemaConfigured):
	AutoTags = ()  # not currently in any interface

	def __init__(self):
		super(Media, self).__init__()

@interface.implementer(nti_interfaces.IMediaSource)
class MediaSource(Media):
	__external_can_create__ = True
	mime_type = mimeType = 'application/vnd.nextthought.embeddedmedia'

@interface.implementer(nti_interfaces.IVideoSource)
class VideoSource(MediaSource):
	__external_can_create__ = True
	mime_type = mimeType = 'application/vnd.nextthought.embeddedvideo'
	createDirectFieldProperties(nti_interfaces.IVideoSource)

@interface.implementer(nti_interfaces.IAudioSource)
class AudioSource(MediaSource):
	__external_can_create__ = True
	mime_type = mimeType = 'application/vnd.nextthought.embeddedaudio'
	createDirectFieldProperties(nti_interfaces.IAudioSource)

@component.adapter(nti_interfaces.IMedia)
class MediaInternalObjectIO(UserContentRootInternalObjectIO):
	ext_iface_upper_bound = nti_interfaces.IMedia
