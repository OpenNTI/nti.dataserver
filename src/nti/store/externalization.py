# -*- coding: utf-8 -*-
"""
Store externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component

from nti.externalization.interfaces import IInternalObjectIO
from nti.externalization.datastructures import InterfaceObjectIO

from . import interfaces

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.IPurchaseAttempt)
class PurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.IPurchaseAttempt

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.IPurchasable)
class PurchasableExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.IPurchasable
