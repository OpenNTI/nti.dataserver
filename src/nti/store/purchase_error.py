# -*- coding: utf-8 -*-
"""
Defines purchase error object.

$Id: purchase_attempt.py 18438 2013-04-19 04:17:47Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component
from zope import interface

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from .utils import MetaStoreObject
from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IPurchaseError)
class PurchaseError(SchemaConfigured):

	__metaclass__ = MetaStoreObject

	# create all interface fields
	createDirectFieldProperties(store_interfaces.IPurchaseError)

	def __str__(self):
		return self.Message

	def __repr__(self):
		return "%s(%s,%s,%s)" % (self.__class__.__name__, self.Type, self.Message, self.Code)

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
