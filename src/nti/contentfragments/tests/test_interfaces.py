#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_

from nti.contentfragments.interfaces import SanitizedHTMLContentFragment, HTMLContentFragment, PlainTextContentFragment

def test_html_math(  ):

	s1 = SanitizedHTMLContentFragment( 'safe' )
	s2 = SanitizedHTMLContentFragment( 'safe2' )
	h1 = HTMLContentFragment( 'unsafe' )


	assert_that( s1 + s2, is_( SanitizedHTMLContentFragment ),
				"Adding two sanitized fragments produces sanitized fragments" )
	assert_that( s1 + s2, is_( 'safesafe2' ) )

	assert_that( s1 + h1, is_( HTMLContentFragment ),
				 'Adding an unsanitized produces unsanitized' )
	assert_that( h1 + s1, is_( HTMLContentFragment ) )
	assert_that( h1 + s1, is_( 'unsafesafe' ) )
	assert_that( s1 + h1, is_( 'safeunsafe' ) )


	assert_that( s1 * 2, is_( SanitizedHTMLContentFragment ),
				 "Multiplication produces the same types" )
	assert_that( h1 * 2, is_( HTMLContentFragment ) )
	assert_that( s1 * 2, is_( 'safesafe' ) )
	assert_that( h1 * 2, is_( 'unsafeunsafe' ) )

	assert_that( 2 * s1, is_( SanitizedHTMLContentFragment ),
				 "Right multiplication produces the same types" )
	assert_that( 2 * h1, is_( HTMLContentFragment ) )
	assert_that( 2 * s1, is_( 'safesafe' ) )
	assert_that( 2 * h1, is_( 'unsafeunsafe' ) )

import mimetypes

def test_mime_types():
	assert_that( mimetypes.guess_type( 'foo.jsonp' ),
				 is_( ('application/json',None) ) )
