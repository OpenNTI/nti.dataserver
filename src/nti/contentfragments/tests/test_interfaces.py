#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_
from nose.tools import assert_raises

import cPickle as pickle

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

from zope import interface
from nti.tests import verifiably_provides
class ITest(interface.Interface):
	pass

def test_cannot_set_attributes_but_can_provide_interfaces_across_pickles():

	for t in SanitizedHTMLContentFragment, HTMLContentFragment, PlainTextContentFragment:
		s1 = t( 'safe' )

		with assert_raises(AttributeError):
			s1.__parent__ = 'foo'

		# If we do sneak one into the dictionary, it doesn't survive pickling
		s1dict = unicode.__getattribute__( s1, '__dict__' )
		s1dict['__parent__'] = 'foo'

		copy = pickle.loads( pickle.dumps( s1 ) )

		assert_that( copy, is_( s1 ) )
		copy_dict = unicode.__getattribute__( copy, '__dict__' )
		assert_that( copy_dict, is_( {} ) )

		# But if they provided extra interfaces, this does persist
		interface.alsoProvides( s1, ITest )

		copy = pickle.loads( pickle.dumps( s1 ) )

		assert_that( copy, verifiably_provides( ITest ) )
