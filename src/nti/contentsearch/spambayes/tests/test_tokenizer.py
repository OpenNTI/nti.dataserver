#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from zope import component

from nti.contentprocessing import interfaces as cp_interfaces

from nti.contentsearch.spambayes.tests import SharedConfiguringTestLayer

class TestTokenzier(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	spam_msg = "Your Status: Approved-Today Today's Date: August 2nd, 2012 Advance Amount: 1,500.00"
	
	def do_tokenize(self, text=None, *args, **kwargs):
		tokenizer = component.getUtility(cp_interfaces.IContentTokenizer, name='spam_tokenizer')
		result = tokenizer.tokenize(text, *args, **kwargs) if text else u''
		return unicode(' '.join(result))

	def test_tokenize(self):
		text = self.do_tokenize(self.spam_msg)
		assert_that(text, is_("your status skip:a 10 today's date august 2nd, 2012 advance amount 1,500.00"))
		
		text = self.do_tokenize(self.spam_msg, max_word_size=20)
		assert_that(text, is_("your status approved-today today's date august 2nd, 2012 advance amount 1,500.00"))
		
		msg = "Serbia is surrounded by NATO members and allies"
		text = self.do_tokenize(msg, max_word_size=4)
		assert_that(text, is_("skip:s 0 skip:s 10 nato skip:m 0 and skip:a 0"))
		
		text = self.do_tokenize(msg, max_word_size=4, generate_long_skips=False)
		assert_that(text, is_("nato and"))
