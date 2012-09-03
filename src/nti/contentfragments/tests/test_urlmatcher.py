from __future__ import print_function, unicode_literals

from nti.tests import ConfiguringTestBase

import nti.contentfragments
from nti.contentfragments import interfaces as frg_interfaces
from nti.contentfragments.urlmatcher import GrubberHyperlinkifier

from hamcrest import assert_that, is_

class TestUrlMatcher(ConfiguringTestBase):
	set_up_packages = (nti.contentfragments,)

	linkifier = GrubberHyperlinkifier()
		
	def test_simple(self):
		html = u'<html><head/><body>ichigo dies in http://www.bleachget.com/watch/bleach-episode-271</body></html>'
		exp = u'<html><head/><body>ichigo dies in <a href="http://www.bleachget.com/watch/bleach-episode-271">' + \
			  u'http://www.bleachget.com/watch/bleach-episode-271</a></body></html>'
		assert_that(self.linkifier.convert(frg_interfaces.IHTMLContentFragment(html)), is_(exp))
		
	def test_double(self):
		html = u'<html><head/><body>yahoo in http://yahoo.com and google in http://www.google.com</body></html>'
		exp = u'<html><head/><body>yahoo in <a href="http://yahoo.com">http://yahoo.com</a> and google in ' + \
			  u'<a href="http://www.google.com">http://www.google.com</a></body></html>'
		assert_that(self.linkifier.convert(frg_interfaces.IHTMLContentFragment(html)), is_(exp))
	
	def test_with_tail(self):
		html = u'<html><head/><body><p>does http://www.facebook.com sucks</p>yes check out http://www.nextthought.com</body></html>'
		exp = u'<html><head/><body><p>does <a href="http://www.facebook.com">http://www.facebook.com</a> sucks</p>' + \
			  u'yes check out <a href="http://www.nextthought.com">http://www.nextthought.com</a></body></html>'
		assert_that(self.linkifier.convert(frg_interfaces.IHTMLContentFragment(html)), is_(exp))
		
	def test_others(self):
		html = u'<html><head/><body>my sec link https://www.chase.com</body></html>'
		exp = u'<html><head/><body>my sec link <a href="https://www.chase.com">https://www.chase.com</a></body></html>'
		assert_that(self.linkifier.convert(frg_interfaces.IHTMLContentFragment(html)), is_(exp))
		html = u'<html><head/><body>search with www.google.com to know everything</body></html>'
		exp = u'<html><head/><body>search with <a href="www.google.com">www.google.com</a> to know everything</body></html>'
		assert_that(self.linkifier.convert(frg_interfaces.IHTMLContentFragment(html)), is_(exp))
		
	def test_nochange(self):
		html = u'<html><head/><body>are we there yet</body></html>'
		assert_that(self.linkifier.convert(frg_interfaces.IHTMLContentFragment(html)), is_(html))
		html = u'<html><head/><body>fly <a href="http://www.aa.com">aa</a> always</body></html>'
		assert_that(self.linkifier.convert(frg_interfaces.IHTMLContentFragment(html)), is_(html))
	
if __name__ == '__main__':
	import unittest
	unittest.main()
