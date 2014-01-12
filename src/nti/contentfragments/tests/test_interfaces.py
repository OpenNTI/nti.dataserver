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
from nti.contentfragments.interfaces import UnicodeContentFragment

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
from nti.testing.matchers import verifiably_provides
class ITest(interface.Interface):
	pass

def test_cannot_set_attributes_but_can_provide_interfaces_across_pickles():

	all_ucf_subclasses = set()
	def r(t):
		if t in all_ucf_subclasses:
			return
		all_ucf_subclasses.add(t)
		for x in t.__subclasses__():
			r(x)
	r(UnicodeContentFragment)
	# Plus some fixed one just 'cause
	all_ucf_subclasses.update( (SanitizedHTMLContentFragment, HTMLContentFragment, PlainTextContentFragment, UnicodeContentFragment) )
	print(all_ucf_subclasses)
	for t in all_ucf_subclasses:
		s1 = t( 'safe' )

		with assert_raises(AttributeError):
			s1.__parent__ = 'foo'

		# If we do sneak one into the dictionary, it doesn't survive pickling
		try:
			s1dict = unicode.__getattribute__( s1, '__dict__' )
			s1dict['__parent__'] = 'foo'
		except AttributeError:
			if t is not UnicodeContentFragment:
				# The root really doesn't allow this,
				# but for some reason of inheritance the
				# subclasses do?
				raise

		copy = pickle.loads( pickle.dumps( s1 ) )

		assert_that( copy, is_( s1 ) )
		try:
			copy_dict = unicode.__getattribute__( copy, '__dict__' )
		except AttributeError:
			if t is not UnicodeContentFragment:
				raise
			copy_dict = {}
		assert_that( copy_dict, is_( {} ) )

		# But if they provided extra interfaces, this does persist
		interface.alsoProvides( s1, ITest )

		copy = pickle.loads( pickle.dumps( s1 ) )

		assert_that( copy, verifiably_provides( ITest ) )

def test_dont_lose_type_on_common_ops():

	for t in SanitizedHTMLContentFragment, HTMLContentFragment, PlainTextContentFragment:
		s1 = t( 'safe' )

		assert_that( s1.translate( {ord('s'): 't'} ), is_( t ) )
		assert_that( s1.translate( {ord('s'): 't'} ), is_( 'tafe') )

		assert_that( unicode(s1), is_( t ) )
