from __future__ import print_function, unicode_literals

from zope import component
from zope import interface

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization import interfaces as ext_interfaces

from . import interfaces as store_interfaces

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(store_interfaces.IPurchaseAttempt)
class _PurchaseAttemptExternalExternalizer(object):
	def __init__( self, purchase ):
		self.purchase = purchase
		
	def toExternalObject(self):
		eo = {
				ext_interfaces.StandardExternalFields.CLASS: 'PurchaseAttempt',
				'State': self.purchase.state,
				'Items': self.purchase.items,	
				'Processor': self.purchase.processor,
				'StartTime': self.purchase.start_time,
				'Endtime': self.purchase.end_time,
				'FailureMessage': self.purchase.failure_message
			 }
		eo[ext_interfaces.StandardExternalFields.OID] = to_external_ntiid_oid(self.purchase)
		eo[ext_interfaces.StandardExternalFields.LAST_MODIFIED] = self.purchase.lastModified
		return eo
