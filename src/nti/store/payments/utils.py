from __future__ import unicode_literals, print_function, absolute_import

import re

from zope import schema

def is_valid_creditcard_number(s):
	"""
	Returns True if the credit card number ``s`` is valid, False otherwise.
	
	http://code.activestate.com/recipes/577838-credit-card-validation/
	http://atlee.ca/blog/2008/05/27/validating-credit-card-numbers-in-python/
	"""
	s = re.sub("[^0-9]", "", str(s))
	regexps = [
			"^4\d{15}$",
			"^5[1-5]\d{14}$",
			"^3[4,7]\d{13}$",
			"^3[0,6,8]\d{12}$",
			"^6011\d{12}$",
	        ]
	
	if not any(re.match(r, s) for r in regexps):
		return False

	# check sum
	ld = [ int(x)*2 for n,x in enumerate(s[::-1]) if n%2 != 0 ]
	la = reduce(lambda x,y: x+y, map(lambda x:list(str(x)), ld))
	lb = [x for n,x in enumerate( s[::-1] ) if n%2 == 0 ]
	chksum = reduce(lambda x,y:int(x)+int(y), la+lb) % 10
	return chksum == 0

digits_re = re.compile('^([0-9][0-9])')

def validate_credit_card(number, exp_month, exp_year, cvc=None):
	if not is_valid_creditcard_number(number):
		raise schema.ValidationError('Invalid credit card number')
	
	if not digits_re.match(exp_month):
		raise schema.ValidationError('Invalid expiration month')
	
	if not digits_re.match(exp_year):
		raise schema.ValidationError('Invalid expiration year')
	
	if cvc and not all([c.isdigit() for c in str(cvc)]):
		raise schema.ValidationError('Invalid CVC number')
		
	return True