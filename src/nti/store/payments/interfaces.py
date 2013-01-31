from __future__ import unicode_literals, print_function, absolute_import

from zope import schema
from zope import interface

class IStripeCustomer(interface.Interface):
	customer_id = schema.Text(title='Custome id', required=True)
	active_card = schema.Text(title='Hash for active card', required=False)
	purchases = schema.Dict(title='Customer purchases',
							key_type=schema.TextLine(title='Purchase id'),
							value_type=schema.TextLine(title='Item purchased (i.e. NTIID)'))