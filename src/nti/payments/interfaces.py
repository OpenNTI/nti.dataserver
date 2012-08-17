from __future__ import print_function, unicode_literals

#from zope import schema
from zope import interface

class IPaymentManager(interface.Interface):
	
	def get_transaction(traxId):
		"""return the detail of a given transaction"""
		
class ICoBrandedPaymentManager(IPaymentManager):
	
	def get_authorization(amount,
						  returnURL,
						  cancelURL=None,
						  currency='USD', 
						  paymentReason=None,
						  **kwargs):
		"""
		return an autorization for the specified request. 
		The autorization has a payment proceessor (ppURL)
		for redirection and dataserver transaction id.
		
		amount: Authorization amount
		returnURL: URL to return after payment operation is performed
		cancelURL: URL to return after payment operation is canceled
		currency: amount currency
		paymentReason: Description of payment
		"""