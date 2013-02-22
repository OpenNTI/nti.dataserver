#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import time
import unittest

from nti.store.payments import _onetimepass as otp

from hamcrest import (assert_that, is_)

class TestOneTimePass(unittest.TestCase):

	secret = 'MFRGGZDFMZTWQ2LK'
	
	def test_is_possible_tokenr(self):
		assert_that(otp.is_possible_token(123456), is_(True))
		assert_that(otp.is_possible_token('123456'), is_(True))
		assert_that(otp.is_possible_token('abcdef'), is_(False))
		assert_that(otp.is_possible_token('12345678'), is_(False))
	
	def test_get_hotp(self):
		assert_that(otp.get_hotp(self.secret, intervals_no=1), is_(765705))
		assert_that(otp.get_hotp(self.secret, intervals_no=2), is_(816065))
		assert_that(otp.get_hotp(self.secret, intervals_no=2, as_string=True), is_('816065'))
	
	def test_get_totp(self):
		assert_that(otp.get_hotp(self.secret, int(time.time())//30), is_(otp.get_totp(self.secret)))
	
	def test_valid_hotp(self):
		assert_that(otp.valid_hotp(713385, self.secret, last=1, trials=5), is_(4))
		assert_that(otp.valid_hotp(865438, self.secret, last=1, trials=5), is_(False))
		assert_that(otp.valid_hotp(865438, self.secret, last=4, trials=5), is_(False))

if __name__ == '__main__':
	unittest.main()
