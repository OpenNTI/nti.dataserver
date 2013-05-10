"""
Defines priceable object.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.mimetype import interfaces as zmime_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.schema import SchemaConfigured

from .utils import MetaStoreObject
from .purchasable import get_purchasable
from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IPriceable, zmime_interfaces.IContentTypeAware)
class Priceable(SchemaConfigured):

	__metaclass__ = MetaStoreObject

	NTIID = FP(store_interfaces.IPriceable['NTIID'])
	Quantity = FP(store_interfaces.IPriceable['Quantity'])

	def copy(self):
		result = self.__class__(NTIID=self.NTIID, Quantity=self.Quantity)
		return result

	@property
	def purchasable(self):
		result = get_purchasable(self.NTIID)
		return result

	@property
	def Currency(self):
		result = getattr(self.purchasable, 'Currency', None)
		return result

	@property
	def Provider(self):
		result = getattr(self.purchasable, 'Provider', None)
		return result

	@property
	def Amount(self):
		result = getattr(self.purchasable, 'Amount', None)
		return result

	@property
	def Fee(self):
		result = getattr(self.purchasable, 'Fee', None)
		return result

	def __str__(self):
		return self.NTIID

	def __repr__(self):
		return "%s(%s,%s)" % (self.__class__.__name__, self.NTIID, self.Quantity)

	def __eq__(self, other):
		try:
			return self is other or (self.NTIID == other.NTIID
									 and self.Quantity == self.Quantity)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.NTIID)
		xhash ^= hash(self.Quantity)
		return xhash

def create_priceable(ntiid, quantity=1):
	quantity = 1 if quantity is None else int(quantity)
	result = Priceable(NTIID=unicode(ntiid), Quantity=quantity)
	return result
