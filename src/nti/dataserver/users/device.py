#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import functools
import collections

import six

from zope import interface

from zope.component.factory import Factory

from nti.dataserver.interfaces import IDevice
from nti.dataserver.interfaces import IZContained
from nti.dataserver.interfaces import IDeviceContainer
from nti.dataserver.interfaces import IHTC_NEW_FACTORY

from nti.datastructures.datastructures import AbstractNamedLastModifiedBTreeContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.datastructures import ExternalizableDictionaryMixin

from nti.externalization.interfaces import StandardExternalFields

from nti.mimetype.mimetype import ModeledContentTypeAwareRegistryMetaclass

logger = __import__('logging').getLogger(__name__)


@six.add_metaclass(ModeledContentTypeAwareRegistryMetaclass)
@functools.total_ordering
@interface.implementer(IDevice, IZContained)
class Device(PersistentCreatedModDateTrackingObject,
             ExternalizableDictionaryMixin):

    __external_can_create__ = True

    __name__ = None
    __parent__ = None

    def __init__(self, deviceId):
        """
        :param deviceId: Either a basic dictionary containing `StandardExternalFields.ID`
               or a string in hex encoding the bytes of a device id.
        """
        super(Device, self).__init__()
        if isinstance(deviceId, collections.Mapping):
            deviceId = deviceId[StandardExternalFields.ID]
        # device id arrives in hex encoding
        self.deviceId = deviceId.decode('hex')

    def get_containerId(self):
        return _DevicesMap.container_name

    def set_containerId(self, cid):
        pass
    containerId = property(get_containerId, set_containerId)

    @property
    def id(self):
        # Make ID not be writable
        return self.deviceId.encode('hex')

    def toExternalObject(self, *args, **kwargs):
        result = super(Device, self).toExternalDictionary(*args, **kwargs)
        return result

    def updateFromExternalObject(self, ext):
        pass

    def __eq__(self, other):
        try:
            return self.deviceId == other.deviceId
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            return self.deviceId < other.deviceId
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return self.deviceId.__hash__()


@interface.implementer(IDeviceContainer)
class _DevicesMap(AbstractNamedLastModifiedBTreeContainer):
    contained_type = IDevice
    container_name = 'Devices'

    __name__ = container_name

    def __setitem__(self, key, value):
        if not isinstance(value, Device):
            value = Device(value)
        super(_DevicesMap, self).__setitem__(key, value)


# pylint: disable=no-value-for-parameter
IDevice.setTaggedValue(IHTC_NEW_FACTORY,
                       Factory(Device, interfaces=(IDevice,)))
