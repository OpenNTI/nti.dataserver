from __future__ import unicode_literals, print_function, absolute_import

import unittest

from nti.store.payments import utils
from nti.store.payments.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestPaymentUtils(ConfiguringTestBase):
	
	def test_is_valid_creditcard_number(self):
		assert_that(utils.is_valid_creditcard_number("4111-1111-1111-1111"), is_(True))
		assert_that(utils.is_valid_creditcard_number("4111 1111 1111 1112"), is_(False))
		assert_that(utils.is_valid_creditcard_number("5105105105105100"), is_(True))
		assert_that(utils.is_valid_creditcard_number(5105105105105100), is_(True))
	
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
			utils.validate_credit_card("5105105105105100", "1", "3", "647")
			self.fail()
		except:
			pass
		
		try:
			utils.validate_credit_card("5105105105105100", "1", "3", "xx")
			self.fail()
		except:
			pass
		
		
if __name__ == '__main__':
	unittest.main()