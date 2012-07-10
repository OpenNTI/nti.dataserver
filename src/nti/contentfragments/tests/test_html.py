#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import os
import plistlib

from hamcrest import assert_that, is_
from nti.tests import verifiably_provides
import nti.tests
import nti.contentfragments
setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.contentfragments,) )
tearDownModule = nti.tests.module_teardown

from nti.contentfragments import interfaces as frg_interfaces


def _check_sanitized( inp, expect, expect_iface=frg_interfaces.IUnicodeContentFragment ):
	was = frg_interfaces.IUnicodeContentFragment( inp )
	__traceback_info__ = inp, type(inp), was, type(was)
	assert_that( was, is_( expect.strip() ) )
	assert_that( was, verifiably_provides( expect_iface ) )
	return was

def test_sanitize_html():
	strings = plistlib.readPlist( os.path.join( os.path.dirname(__file__), 'contenttypes-notes-tosanitize.plist' ) )
	sanitized = open( os.path.join( os.path.dirname( __file__ ), 'contenttypes-notes-sanitized.txt' ) ).readlines()
	for s in zip(strings,sanitized):
		yield _check_sanitized, s[0], s[1]

def test_sanitize_data_uri():
	_ = _check_sanitized( "<audio src='data:foobar' controls />",
							 u'<html><body><audio controls="" src="data:foobar"></audio></body></html>')


def test_normalize_html_text_to_par():
	html = u'<html><body><p style=" text-align: left;"><span style="font-family: \'Helvetica\';  font-size: 12pt; color: black;">The pad replies to my note.</span></p>The server edits it.</body></html>'
	exp =  u'<html><body><p style="text-align: left;"><span>The pad replies to my note.</span></p><p style="text-align: left;">The server edits it.</p></body></html>'
	sanitized = _check_sanitized( html, exp, frg_interfaces.ISanitizedHTMLContentFragment )

	plain_text = frg_interfaces.IPlainTextContentFragment( sanitized )
	assert_that( plain_text, verifiably_provides( frg_interfaces.IPlainTextContentFragment ) )
	assert_that( plain_text, is_( "The pad replies to my note.The server edits it." ) )


def test_html_to_text():
	exp =  frg_interfaces.HTMLContentFragment( '<html><body><p style="text-align: left;"><span>The pad replies to my note.</span></p><p style="text-align: left;">The server edits it.</p></body></html>' )

	plain_text = frg_interfaces.IPlainTextContentFragment( exp )
	assert_that( plain_text, verifiably_provides( frg_interfaces.IPlainTextContentFragment ) )
	assert_that( plain_text, is_( "The pad replies to my note.The server edits it." ) )
