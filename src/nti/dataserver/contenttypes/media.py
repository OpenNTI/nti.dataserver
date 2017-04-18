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

from nti.dataserver.contenttypes.base import UserContentRoot
from nti.dataserver.contenttypes.base import UserContentRootInternalObjectIO

from nti.dataserver.interfaces import IMedia
from nti.dataserver.interfaces import IZContained
from nti.dataserver.interfaces import IEmbeddedMedia
from nti.dataserver.interfaces import IEmbeddedAudio
from nti.dataserver.interfaces import IEmbeddedVideo

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.threadable.threadable import Threadable as ThreadableMixin


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
