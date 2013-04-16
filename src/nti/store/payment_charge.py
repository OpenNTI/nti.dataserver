# -*- coding: utf-8 -*-
"""
Defines purchase charge object.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import functools
from datetime import datetime

from zope import interface
from zope.mimetype import interfaces as zmime_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.schema import SchemaConfigured

from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IUserAddress, zmime_interfaces.IContentTypeAware)
class UserAddress(SchemaConfigured):

	Street = FP(store_interfaces.IUserAddress['Street'])
	City = FP(store_interfaces.IUserAddress['City'])
	State = FP(store_interfaces.IUserAddress['State'])
	Zip = FP(store_interfaces.IUserAddress['Zip'])
	Country = FP(store_interfaces.IUserAddress['Country'])

	def __str__(self):
		return "%s\n%s,%s %s\n%s" % (self.Street, self.City, self.State, self.Zip, self.Country)

	__repr__ = __str__

	def __eq__(self, other):
		return self is other or (isinstance(other, UserAddress)
 								 and self.Zip == other.Zip
 								 and self.City == other.City
 								 and self.State == other.State
 								 and self.Street == other.Street
 								 and self.Country == other.Country)

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Zip)
		xhash ^= hash(self.City)
		xhash ^= hash(self.State)
		xhash ^= hash(self.Street)
		xhash ^= hash(self.Country)
		return xhash

	@classmethod
	def create(cls, address_line1, address_line2=None, city=None, state=None, zip_=None, country=None):
		result = None
		zip_ = zip_ or store_interfaces.IUserAddress['Zip'].default
		country = country or store_interfaces.IUserAddress['Country'].default
		if address_line1 and city:
			street = "%s\n%s" % (address_line1, address_line2 or u'')
			result = UserAddress(Street=street.strip(), City=city, State=state, Zip=zip_, Country=country)
		return result

@functools.total_ordering
@interface.implementer(store_interfaces.IPaymentCharge, zmime_interfaces.IContentTypeAware)
class PaymentCharge(SchemaConfigured):

	Amount = FP(store_interfaces.IPaymentCharge['Amount'])
	Currency = FP(store_interfaces.IPaymentCharge['Currency'])
	Created = FP(store_interfaces.IPaymentCharge['Created'])
	CardLast4 = FP(store_interfaces.IPaymentCharge['CardLast4'])
	Address = FP(store_interfaces.IPaymentCharge['Address'])
	Name = FP(store_interfaces.IPaymentCharge['Name'])

	def __str__(self):
		return "%s:%s" % (self.Currency, self.Amount)

	def __repr__(self):
		d = datetime.fromtimestamp(self.Created)
		return "%s(%s,%s,%s)" % (self.__class__, d, self.Currency, self.Amount)

	def __eq__(self, other):
		return self is other or (isinstance(other, PaymentCharge)
								 and self.Amount == other.Amount
								 and self.Created == other.Created
								 and self.Currency == other.Currency
								 and self.Name == other.Name)

	def __lt__(self, other):
		try:
			return self.Created < other.Created
		except AttributeError:
			return NotImplemented

	def __gt__(self, other):
		try:
			return self.Created > other.Created
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Amount)
		xhash ^= hash(self.Created)
		xhash ^= hash(self.Currency)
		xhash ^= hash(self.Name)
		return xhash
