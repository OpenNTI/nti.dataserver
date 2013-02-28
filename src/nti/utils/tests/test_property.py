#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.annotation import interfaces as an_interfaces

from ..property import dict_alias, annotation_alias, CachedProperty

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_property
from hamcrest import same_instance
from hamcrest import is_

def test_dict_alias():
	class X(object):
		def __init__( self ):
			self.x = 1

		y = dict_alias( 'x' )

	assert_that( X(), has_property( 'y', 1 ) )
	x = X()
	x.y = 2
	assert_that( x, has_property( 'y', 2 ) )
	assert_that( x, has_property( 'x', 2 ) )


def test_annotation_alias():

	@interface.implementer(an_interfaces.IAnnotations)
	class X(dict):

		the_alias = annotation_alias( 'the.key', delete=True, default=1 )

	x = X()
	# Default value
	assert_that( x, has_property( 'the_alias', 1 ) )

	# Set
	x.the_alias = 2
	assert_that( x, has_property( 'the_alias', 2 ) )
	assert_that( x, has_entry( 'the.key', 2 ) )

	# del
	del x.the_alias
	assert_that( x, has_property( 'the_alias', 1 ) )

	# quiet re-del
	del x.the_alias
	assert_that( x, has_property( 'the_alias', 1 ) )

def test_cached_property():

	# Usable directly

	class X(object):

		@CachedProperty
		def prop(self):
			return object()

	x = X()
	assert_that( x.prop, same_instance( x.prop ) )

	# Usable with names

	class Y(object):

		def __init__( self ):
			self.dep = 1

		@CachedProperty('dep')
		def prop(self):
			return str(self.dep)

	y = Y()
	assert_that( y.prop, same_instance( y.prop ) )
	assert_that( y.prop, is_( "1" ) )
	y.dep = 2
	assert_that( y.prop, is_( "2" ) )
	assert_that( y.prop, same_instance( y.prop ) )

	# And, to help refactoring, usable with parens but no names
	class Z(object):
		@CachedProperty()
		def prop(self):
			return object()

	z = Z()
	assert_that( z.prop, same_instance( z.prop ) )
