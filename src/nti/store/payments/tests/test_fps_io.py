#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import os
import unittest
import urlparse

from nti.store.payments import fps_io

from hamcrest import (assert_that, instance_of, is_not)
			
class TestFPSIO(unittest.TestCase):
	
	@classmethod
	def setUpClass(cls):
		super(TestFPSIO,cls).setUpClass()
		os.environ['AWS_ACCESS_KEY_ID'] = u'AKIAJWVTIPBU7QCJUYUA'
		os.environ['AWS_SECRET_ACCESS_KEY'] = u'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'
		cls.fpsio = fps_io.FPSIO()
		
	@classmethod
	def tearDownClass(cls):
		super(TestFPSIO,cls).tearDownClass()
		os.environ.pop('AWS_ACCESS_KEY_ID', None)
		os.environ.pop('AWS_SECRET_ACCESS_KEY', None)
		
	def test_signature(self):
		s = self.fpsio.signature()
		assert_that(s, is_not(None))
		s = self.fpsio.signature('foo')
		assert_that(s, is_not(None))
		
	def test_cbi_url(self):
		s = self.fpsio.get_cbui_url('http://localhost', 300, payment_reason='payment')
		assert_that(s, is_not(None))
		urlparse.urlparse(s)
		
	def test_get_account_activity(self):
		trxs = self.fpsio.get_account_activity()
		assert_that(trxs, instance_of(list))
		
	def test_get_account_balance(self):
		balance = self.fpsio.get_account_balance()
		assert_that(balance, is_not(None))
		
if __name__ == '__main__':
	unittest.main()
