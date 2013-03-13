# -*- coding: utf-8 -*-
"""
Defines purchase charge object.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time
import functools
from datetime import datetime

from zope import interface

from nti.utils.property import alias

from . import interfaces as store_interfaces

# class UserAddress(interface.Interface):
#
# 	Zip = u''
# 	State = u''
# 	Country = 'USA'
#
# 	def __init__(self, street, city, state, zip_=None, country='USA'):
# 		self.City = city
# 		self.Street = street
# 		if zip_:
# 			self.Zip = zip_
# 		if state:
# 			self.State = state
# 		if country and country != self.Country:
# 			self.Country = country
#
# 	zip = alias('Zip')
# 	city = alias('City')
# 	state = alias('State')
# 	street = alias('Street')
# 	country = alias('Country')
#
# 	def __str__(self):
# 		return "%s\n%s,%s %s\n%s" % (self.street, self.city, self.state, self.zip, self.country)
#
# 	__repr__ = __str__
#
# 	def __eq__(self, other):
# 		return self is other or (isinstance(other, UserAddress)
# 								 and self.zip == other.zip
# 								 and self.city == other.city
# 								 and self.state == other.state
# 								 and self.street == other.street
# 								 and self.country == other.country)
#
# 	def __hash__(self):
# 		xhash = 47
# 		xhash ^= hash(self.zip)
# 		xhash ^= hash(self.city)
# 		xhash ^= hash(self.state)
# 		xhash ^= hash(self.street)
# 		xhash ^= hash(self.country)
# 		return xhash
#
# 	@classmethod
# 	def create(cls, address_line1, address_line2=None, city=None, state=None, zip_=None, country='USA'):
# 		result = None
# 		if address_line1 and city and country:
# 			street = "%s\n%s" % (address_line1, address_line2 or u'')
# 			result = UserAddress(street.strip(), city, state, zip_, country)
# 		return result

@functools.total_ordering
@interface.implementer(store_interfaces.IPaymentCharge)
class PaymentCharge(object):

	Name = None
	Amount = None
	Address = None
	Currency = 'USD'
	CardLast4 = None

	def __init__(self, amount, currency='USD', created=None, last4=None, address=None, name=None):
		self.Amount = amount
		self.Created = created or time.time()
		if name:
			self.Name = name
		if address:
			self.Address = address
		if last4:
			self.CardLast4 = last4
		if currency and currency != self.Currency:
			self.Currency = currency

	name = alias('Name')
	amount = alias('Amount')
	last4 = alias('CardLast4')
	address = alias('Address')
	created = alias('Created')
	currency = alias('Currency')

	def __str__(self):
		return "%s:%s" % (self.currency, self.amount)

	def __repr__(self):
		d = datetime.fromtimestamp(self.created)
		return "%s(%s,%s,%s)" % (self.__class__, d, self.currency, self.amount)

	def __eq__(self, other):
		return self is other or (isinstance(other, PaymentCharge)
								 and self.amount == other.amount
								 and self.created == other.created
								 and self.currency == other.currency
								 and self.name == other.name)

	def __lt__(self, other):
		try:
			return self.created < other.created
		except AttributeError:
			return NotImplemented

	def __gt__(self, other):
		try:
			return self.created > other.created
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.amount)
		xhash ^= hash(self.created)
		xhash ^= hash(self.currency)
		xhash ^= hash(self.name)
		return xhash
