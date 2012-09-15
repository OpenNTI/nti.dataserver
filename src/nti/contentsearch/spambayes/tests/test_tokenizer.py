import unittest

from zope import component

from nti.contentsearch import interfaces as cs_interfaces

from nti.contentsearch.spambayes.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestTokenzier(ConfiguringTestBase):

	spam_msg = "Your Status: Approved-Today Today's Date: August 2nd, 2012 Advance Amount: 1,500.00"
	
	def do_tokenize(self, text=None, *args, **kwargs):
		tokenizer = component.getUtility(cs_interfaces.IContentTokenizer, name='spam_tokenizer')
		result = tokenizer.tokenize(text, *args, **kwargs) if text else u''
		return unicode(' '.join(result))

	def test_tokenize(self):
		text = self.do_tokenize(self.spam_msg)
		assert_that(text, is_("your status: skip:a 10 today's date: august 2nd, 2012 advance amount: 1,500.00"))
		
		text = self.do_tokenize(self.spam_msg, maxword=20)
		assert_that(text, is_("your status: approved-today today's date: august 2nd, 2012 advance amount: 1,500.00"))
		
		msg = "Serbia is surrounded by NATO members and allies"
		text = self.do_tokenize(msg, maxword=4)
		assert_that(text, is_("skip:s 0 skip:s 10 nato skip:m 0 and skip:a 0"))
		
		text = self.do_tokenize(msg, maxword=4, generate_long_skips=False)
		assert_that(text, is_("nato and"))
		
if __name__ == '__main__':
	unittest.main()
