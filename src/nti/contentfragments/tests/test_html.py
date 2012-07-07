#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import os
import plistlib

from hamcrest import assert_that, is_

from nti.contentfragments.html import sanitize_user_html

def _check_sanitized( inp, expect ):
	was = sanitize_user_html( inp )
	assert_that( was, is_( expect.strip() ) )

def test_sanitize_html():
	strings = plistlib.readPlist( os.path.join( os.path.dirname(__file__), 'contenttypes-notes-tosanitize.plist' ) )
	sanitized = open( os.path.join( os.path.dirname( __file__ ), 'contenttypes-notes-sanitized.txt' ) ).readlines()
	for s in zip(strings,sanitized):
		yield _check_sanitized, s[0], s[1]

def test_sanitize_data_uri():
	_check_sanitized( "<audio src='data:foobar' controls />",
					  u'<html><body><audio controls="" src="data:foobar"></audio></body></html>')


def test_normalize_html_text_to_par():
	html = u'<html><body><p style=" text-align: left;"><span style="font-family: \'Helvetica\';  font-size: 12pt; color: black;">The pad replies to my note.</span></p>The server edits it.</body></html>'
	exp =  u'<html><body><p style="text-align: left;"><span>The pad replies to my note.</span></p><p style="text-align: left;">The server edits it.</p></body></html>'
	_check_sanitized( html, exp )
