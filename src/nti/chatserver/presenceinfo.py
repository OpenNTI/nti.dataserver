#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the presence-related objects.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from zope import component
from zope import interface

from zope.component.factory import Factory

from nti.base.interfaces import ILastModified

from nti.chatserver.interfaces import IPresenceInfo
from nti.chatserver.interfaces import IUnattachedPresenceInfo

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.representation import WithRepr

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import PermissiveSchemaConfigured as SchemaConfigured

LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED

logger = __import__('logging').getLogger(__name__)


@WithRepr
@interface.implementer(IPresenceInfo)
class PresenceInfo(SchemaConfigured):  # NOT persistent
    createDirectFieldProperties(IUnattachedPresenceInfo)
    createDirectFieldProperties(IPresenceInfo)
    createDirectFieldProperties(ILastModified)

    createdTime = alias('lastModified')  # overwrite

    __external_can_create__ = True
    mimeType = nti_mimetype_with_class('presenceinfo')

    def __init__(self, *args, **kwargs):
        self.lastModified = time.time()
        super(PresenceInfo, self).__init__(*args, **kwargs)

    def isAvailable(self):
        return self.type == 'available'

PresenceInfoFactory = Factory(PresenceInfo)


@component.adapter(IPresenceInfo)
class PresenceInfoInternalObjectIO(InterfaceObjectIO):
    """
    We are different in that we allow setting Last Modified from the external object. 
    This is because we tend to store this object in its JSON form in redis and would 
    like to maintain that info.
    """
    _ext_iface_upper_bound = IPresenceInfo

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        super(PresenceInfoInternalObjectIO, self).updateFromExternalObject(parsed, *args, **kwargs)
        if LAST_MODIFIED in parsed:
            self._ext_self.lastModified = parsed[LAST_MODIFIED]
