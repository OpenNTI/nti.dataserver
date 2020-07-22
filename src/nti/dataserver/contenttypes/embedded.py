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

from nti.dataserver.interfaces import IEmbeddedLink

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


@interface.implementer(IEmbeddedLink, IContained)
class EmbeddedLink(ThreadableMixin, UserContentRoot, SchemaConfigured):

    createDirectFieldProperties(IEmbeddedLink)

    __name__ = None
    __parent__ = None


@component.adapter(IEmbeddedLink)
class EmbeddedLinkInternalObjectIO(UserContentRootInternalObjectIO):
    ext_iface_upper_bound = IEmbeddedLink


@component.adapter(IEmbeddedLink)
@interface.implementer(IInternalObjectExternalizer)
class _EmbeddedLinkExporter(InterfaceObjectIO):

    _ext_iface_upper_bound = IEmbeddedLink

    def toExternalObject(self, **kwargs):
        context = self._ext_replacement()
        [kwargs.pop(x, None) for x in ('name', 'decorate')]
        adapter = IInternalObjectExternalizer(context, None)
        if adapter is not None:
            result = adapter.toExternalObject(decorate=False, **kwargs)
        else:
            result = super(_EmbeddedLinkExporter, self).toExternalObject(decorate=False,
                                                                  **kwargs)
            decorateMimeType(context, result)
        [result.pop(x, None) for x in (OID, NTIID)]
        return result
