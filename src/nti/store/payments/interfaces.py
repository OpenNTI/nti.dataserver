from __future__ import print_function, unicode_literals

from zope import schema
from zope import interface

class IAuthorization(interface.Interface):
	transactionId = schema.TextLine(title='Transaction id',
									description='NTI transaction id',
							  		required=True)
	
class ICoBrandedAuthorization(IAuthorization):
	cbuiURL = schema.TextLine(title='CoBranded UI URL',
							  description='URL for payment processor',
							  required=True)
	
	returnURL = schema.TextLine(title='Return UI URL',
							  	description='URL for payment processor',
								required=True)
	
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
		The autorization has a payment proceessor (cbuiURL)
		for redirection and dataserver transaction id.
		
		amount: Authorization amount
		returnURL: URL to return after payment operation is performed
		cancelURL: URL to return after payment operation is canceled
		currency: amount currency
		paymentReason: Description of payment
		"""
