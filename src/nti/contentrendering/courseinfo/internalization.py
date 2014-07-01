#!/usr/bin/env python
# -*- coding: utf-8 -*

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import InterfaceObjectIO

from . import interfaces


@interface.implementer(ext_interfaces.IInternalObjectUpdater)
class _NTIPrerequisiteUpdater(object):

    model_interface = interfaces.IPrerequisite
    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        oid  = parsed.get('id') or parsed.get('ID')
        result = InterfaceObjectIO(
                    self.obj,
                    self.model_interface).updateFromExternalObject(parsed)
        assert oid, 'must provide prerequisite id'
        self.obj.id = oid
        return result


@interface.implementer(ext_interfaces.IInternalObjectUpdater)
class _NTICourseInfoUpdater(object):

    model_interface = interfaces.ICourseInfo
    def __init__(self, obj):
        self.obj = obj

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        oid  = parsed.get('id') or parsed.get('ID')
        result = InterfaceObjectIO(
                    self.obj,
                    self.model_interface).updateFromExternalObject(parsed)
        assert oid, 'must provide course id'
        self.obj.id = oid
        return result