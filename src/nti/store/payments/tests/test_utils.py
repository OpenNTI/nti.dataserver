from __future__ import unicode_literals, print_function, absolute_import

import unittest

from nti.store.payments import utils

from hamcrest import (assert_that, is_)

class TestPaymentUtils(unittest.TestCase):
	
	def test_is_valid_creditcard_number(self):
		assert_that(utils.is_valid_creditcard_number("4111-1111-1111-1111"), is_(True))
		assert_that(utils.is_valid_creditcard_number("4111 1111 1111 1112"), is_(False))
		assert_that(utils.is_valid_creditcard_number("5105105105105100"), is_(True))
		assert_that(utils.is_valid_creditcard_number(5105105105105100), is_(True))
		assert_that(utils.is_valid_creditcard_number("111"), is_(False))
		assert_that(utils.is_valid_creditcard_number("5105105105105XY0"), is_(False))
		
	def test_validate_credit_card(self):
		utils.validate_credit_card(5105105105105100, "01", "12", "647")
		try:
			utils.validate_credit_card(5105105105105101, "01", "12", "647")
			self.fail()
		except:
			pass
		
		try:
			utils.validate_credit_card("5105105105105100", "1", "12", "647")
			self.fail()
		except:
			pass
		
		try:
			utils.validate_credit_card("5105105105105100", "10", "3", "647")
			self.fail()
		except:
			pass
		
		try:
			utils.validate_credit_card("5105105105105100", "01", "13", "xx")
			self.fail()
		except:
			pass
		
		
if __name__ == '__main__':
	unittest.main()