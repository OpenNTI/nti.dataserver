# -*- coding: utf-8 -*-
"""
Stripe externalization

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
@component.adapter(interfaces.IStripeConnectKey)
class StripeConnectKeyExternal(InterfaceObjectIO):
	
	_ext_iface_upper_bound = interfaces.IStripeConnectKey
	
	def toExternalObject( self, mergeFrom=None ):
		result = super(StripeConnectKeyExternal, self).toExternalObject(mergeFrom)
		result.pop('PrivateKey', None)
		result.pop('RefreshToken', None)
		return result
