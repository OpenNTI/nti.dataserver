#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Defines purchase error object.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.externalization.externalization import make_repr

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import utils
from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IPurchaseError)
class PurchaseError(SchemaConfigured):

	__metaclass__ = utils.MetaStoreObject

	createDirectFieldProperties(store_interfaces.IPurchaseError)

	def __str__(self):
		return self.Message

	__repr__ = make_repr()

	def __eq__(self, other):
		try:
			return self is other or (self.Type == other.Type
									 and self.Code == other.Code
									 and self.Message == other.Message)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Type)
		xhash ^= hash(self.Code)
		xhash ^= hash(self.Message)
		return xhash

def create_purchase_error(message, type_=None, code=None):
	result = PurchaseError(Message=message, Type=type_, Code=code)
	return result

@component.adapter(store_interfaces.INTIStoreException)
@interface.implementer(store_interfaces.IPurchaseError)
def nti_store_exception_adpater(error):
	result = PurchaseError(Type=u"NTIException")
	args = getattr(error, 'args', ())
	message = unicode(' '.join(map(str, args)))
	result.Message = message or 'Unspecified Exception'
	return result
