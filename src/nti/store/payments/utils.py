# -*- coding: utf-8 -*-
"""
Payment utilities

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import numbers

from zope import schema
from z3c.schema.payments import ISO7812CreditCard
from z3c.schema.payments import isValidCreditCard
from z3c.schema.payments import NotValidISO7812CreditCard
_cc = ISO7812CreditCard()

def is_valid_creditcard_number(s):
	"""
	Returns True if the credit card number ``s`` is valid, False otherwise.

	"""

	if isinstance(s, numbers.Integral):
		s = str(s)
	elif isinstance(s, basestring):
		# Drop spaces and dashes, commonly entered by humans
		# Anything else we consider invalid
		s = s.replace(' ', '').replace('-', '')
	else:
		return False

	return _cc.constraint(s) and isValidCreditCard(s)

_digits_re = re.compile('^([0-9][0-9])')

def validate_credit_card(number, exp_month, exp_year, cvc=None):
	if not is_valid_creditcard_number(number):
		raise NotValidISO7812CreditCard(number)

	if not _digits_re.match(exp_month):
		raise schema.ValidationError('Invalid expiration month')

	if not _digits_re.match(exp_year):
		raise schema.ValidationError('Invalid expiration year')

	if cvc and not all([c.isdigit() for c in str(cvc)]):
		raise schema.ValidationError('Invalid CVC number')

	return True
