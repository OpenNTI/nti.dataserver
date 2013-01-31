from __future__ import unicode_literals, print_function, absolute_import

from zope import schema
from zope import interface

class IStripeCustomer(interface.Interface):
	customer_id = schema.Text(title='Custome id', required=True)
	card = schema.Text(title='Token for last card use', required=False)
	charges = schema.Dict(title='Customer purchase charges',
							key_type=schema.TextLine(title='charge id'),
							value_type=schema.TextLine(title='item purchased id (i.e. NTIID)'))