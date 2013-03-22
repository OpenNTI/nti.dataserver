#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import plistlib

import nti.contentfragments
from nti.contentfragments import interfaces as frg_interfaces

from nti.tests import verifiably_provides
from nti.tests import SharedConfiguringTestBase

from hamcrest import assert_that, is_

def _check_sanitized(inp, expect, expect_iface=frg_interfaces.IUnicodeContentFragment):
	was = frg_interfaces.IUnicodeContentFragment(inp)
	__traceback_info__ = inp, type(inp), was, type(was)
	assert_that(was, is_(expect.strip()))
	assert_that(was, verifiably_provides(expect_iface))
	return was

class TestHtml(SharedConfiguringTestBase):

	set_up_packages = (nti.contentfragments,)

	def test_sanitize_html(self):
		strings = plistlib.readPlist(os.path.join(os.path.dirname(__file__), 'contenttypes-notes-tosanitize.plist'))
		sanitized = open(os.path.join(os.path.dirname(__file__), 'contenttypes-notes-sanitized.txt')).readlines()
		for s in zip(strings, sanitized):
			yield _check_sanitized, s[0], s[1]

	def test_sanitize_data_uri(self):
		_ = _check_sanitized("<audio src='data:foobar' controls />",
							 u'<html><body><audio controls="" src="data:foobar"></audio></body></html>')

	def test_normalize_html_text_to_par(self):
		html = u'<html><body><p style=" text-align: left;"><span style="font-family: \'Helvetica\';  font-size: 12pt; color: black;">The pad replies to my note.</span></p>The server edits it.</body></html>'
		exp = u'<html><body><p style="text-align: left;"><span>The pad replies to my note.</span></p><p style="text-align: left;">The server edits it.</p></body></html>'
		sanitized = _check_sanitized(html, exp, frg_interfaces.ISanitizedHTMLContentFragment)

		plain_text = frg_interfaces.IPlainTextContentFragment(sanitized)
		assert_that(plain_text, verifiably_provides(frg_interfaces.IPlainTextContentFragment))
		assert_that(plain_text, is_("The pad replies to my note.The server edits it."))

	def test_html_to_text(self):
		exp = frg_interfaces.HTMLContentFragment('<html><body><p style="text-align: left;"><span>The pad replies to my note.</span></p><p style="text-align: left;">The server edits it.</p></body></html>')

		plain_text = frg_interfaces.IPlainTextContentFragment(exp)
		assert_that(plain_text, verifiably_provides(frg_interfaces.IPlainTextContentFragment))
		assert_that(plain_text, is_("The pad replies to my note.The server edits it."))

	def test_rejected_tags(self):
		html = u'<html><body><div style=" text-align: left;">The text</div></body></html>'
		exp = 'The text'
		_check_sanitized(html, exp, frg_interfaces.IPlainTextContentFragment)

		html = u'<html><body><style>* { font: "Helvetica";}</style><p style=" text-align: left;">The text</div></body></html>'
		exp = u'<html><body><p style="text-align: left;">The text</p></body></html>'
		_check_sanitized(html, exp, frg_interfaces.ISanitizedHTMLContentFragment)

		html = u'<html><body><script><p>should be ignored</p> Other stuff.</script><p style=" text-align: left;">The text</div></body></html>'
		exp = u'<html><body><p style="text-align: left;">The text</p></body></html>'
		_check_sanitized(html, exp, frg_interfaces.ISanitizedHTMLContentFragment)

		html = 'foo<div><br></div><div>http://google.com</div><div><br></div><div>bar</div><div><br></div><div>http://yahoo.com</div>'''
		exp = '<html><body>foo <br />  <a href="http://google.com">http://google.com</a>  <br />  bar  <br />  <a href="http://yahoo.com">http://yahoo.com</a> </body></html>'
		_check_sanitized(html, exp, frg_interfaces.ISanitizedHTMLContentFragment)

	def test_blog_html_to_text(self):
		exp = u'<html><body>Independence<br />America<br />Expecting<br />Spaces</body></html>'
		plain_text = frg_interfaces.IPlainTextContentFragment(exp)
		assert_that(plain_text, verifiably_provides(frg_interfaces.IPlainTextContentFragment))
		assert_that(plain_text, is_("Independence\nAmerica\nExpecting\nSpaces"))
