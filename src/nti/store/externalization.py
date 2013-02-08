# -*- coding: utf-8 -*-
"""
Store externalization

$Id: externalization.py 15718 2013-02-08 03:30:41Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component

from nti.externalization.datastructures import InterfaceObjectIO
from nti.externalization.interfaces import IInternalObjectIO

from . import interfaces

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.IPurchaseAttempt)
class PurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.IPurchaseAttempt
