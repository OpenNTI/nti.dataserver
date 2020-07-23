#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of media types.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.location.interfaces import IContained

from nti.dataserver.contenttypes.base import UserContentRoot
from nti.dataserver.contenttypes.base import UserContentRootInternalObjectIO

from nti.dataserver.interfaces import IMedia
from nti.dataserver.interfaces import IEmbeddedMedia
from nti.dataserver.interfaces import IEmbeddedAudio
from nti.dataserver.interfaces import IEmbeddedVideo

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.mimetype.externalization import decorateMimeType

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.threadable.threadable import Threadable as ThreadableMixin

OID = StandardExternalFields.OID
NTIID = StandardExternalFields.NTIID

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IMedia, IContained)
class Media(ThreadableMixin, UserContentRoot, SchemaConfigured):

    AutoTags = ()  # not currently in any interface

    __name__ = None
    __parent__ = None

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


@component.adapter(IMedia)
@interface.implementer(IInternalObjectExternalizer)
class _MediaExporter(InterfaceObjectIO):

    _ext_iface_upper_bound = IMedia

    def toExternalObject(self, **kwargs):
        context = self._ext_replacement()
        kwargs.pop('name', None)
        kwargs['decorate'] = False
        externalizer = IInternalObjectExternalizer(context, None) or super(_MediaExporter, self)
        result = externalizer.toExternalObject(**kwargs)
        decorateMimeType(context, result)
        for ext_key in (OID, NTIID):
            result.pop(ext_key, None)
        return result
