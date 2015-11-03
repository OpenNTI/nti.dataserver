#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of media types.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from zope.container.contained import Contained

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from ..interfaces import IMedia
from ..interfaces import IZContained
from ..interfaces import IEmbeddedMedia
from ..interfaces import IEmbeddedAudio
from ..interfaces import IEmbeddedVideo

from .base import UserContentRoot
from .base import UserContentRootInternalObjectIO

from .threadable import ThreadableMixin

@interface.implementer(IMedia, IZContained)
class Media(ThreadableMixin, UserContentRoot, Contained, SchemaConfigured):
	AutoTags = ()  # not currently in any interface

	def __init__(self):
		super(Media, self).__init__()

@interface.implementer(IEmbeddedMedia)
class EmbeddedMedia(Media):
	createDirectFieldProperties(IEmbeddedMedia)

@interface.implementer(IEmbeddedVideo)
class EmbeddedVideo(EmbeddedMedia):
	createDirectFieldProperties(IEmbeddedVideo)

@interface.implementer(IEmbeddedAudio)
class EmbeddedAudio(EmbeddedMedia):
	createDirectFieldProperties(IEmbeddedAudio)

@component.adapter(IMedia)
class MediaInternalObjectIO(UserContentRootInternalObjectIO):
	ext_iface_upper_bound = IMedia
