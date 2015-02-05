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
from zope.container import contained as zcontained

from nti.dataserver import interfaces as nti_interfaces

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .base import UserContentRoot
from .threadable import ThreadableMixin
from .base import UserContentRootInternalObjectIO

@interface.implementer(nti_interfaces.IMedia, nti_interfaces.IZContained)
class Media(ThreadableMixin, UserContentRoot, zcontained.Contained, SchemaConfigured):
	AutoTags = ()  # not currently in any interface

	def __init__(self):
		super(Media, self).__init__()

@interface.implementer(nti_interfaces.IEmbeddedMedia)
class EmbeddedMedia(Media):
	pass

@interface.implementer(nti_interfaces.IEmbeddedVideo)
class EmbeddedVideo(EmbeddedMedia):
	createDirectFieldProperties(nti_interfaces.IEmbeddedVideo)

@interface.implementer(nti_interfaces.IEmbeddedAudio)
class EmbeddedAudio(EmbeddedMedia):
	createDirectFieldProperties(nti_interfaces.IEmbeddedAudio)

@component.adapter(nti_interfaces.IMedia)
class MediaInternalObjectIO(UserContentRootInternalObjectIO):
	ext_iface_upper_bound = nti_interfaces.IMedia
