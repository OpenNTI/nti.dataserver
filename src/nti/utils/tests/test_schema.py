#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_property
from hamcrest import has_length
from hamcrest import contains
from hamcrest import has_entry
from nose.tools import assert_raises

from nti.tests import verifiably_provides, validated_by, not_validated_by

from nti.utils.schema import HTTPURL, Variant, ObjectLen, Object
from nti.utils.schema import IVariant
from nti.utils.schema import Number
from nti.utils.schema import ListOrTuple
from nti.utils.schema import ValidTextLine as TextLine
from nti.utils.schema import IBeforeSequenceAssignedEvent
from nti.utils.schema import IBeforeDictAssignedEvent

from dolmen.builtins import IUnicode
from zope.interface.common import interfaces as cmn_interfaces

from zope.schema import interfaces as sch_interfaces
from zope.schema import Dict
from zope.schema.interfaces import InvalidURI


def test_http_url():

	http = HTTPURL(__name__='foo')

	assert_that( http.fromUnicode( 'www.google.com' ),
				 is_( 'http://www.google.com' ) )

	assert_that( http.fromUnicode( 'https://www.yahoo.com' ),
				 is_( 'https://www.yahoo.com' ) )

	with assert_raises( InvalidURI ) as ex:
		http.fromUnicode( 'mailto:jason@nextthought.com' )


	assert_that( ex.exception, has_property( 'field', http ) )
	assert_that( ex.exception, has_property( 'value', 'mailto:jason@nextthought.com' ) )
	assert_that( ex.exception, has_property( 'message', 'The specified URI is not valid.' ) )



def test_variant( ):

	syntax_or_lookup = Variant( (Object(cmn_interfaces.ISyntaxError),Object(cmn_interfaces.ILookupError), Object(IUnicode)) )

	assert_that( syntax_or_lookup, verifiably_provides( IVariant ) )

	# validates
	assert_that( SyntaxError(), validated_by( syntax_or_lookup ) )
	assert_that( LookupError(), validated_by( syntax_or_lookup ) )

	# doesn't validate
	assert_that( b'foo', not_validated_by( syntax_or_lookup ) )

	assert_that( syntax_or_lookup.fromObject( 'foo' ), is_( 'foo' ) )

	with assert_raises( TypeError ):
		syntax_or_lookup.fromObject( object() )


def test_complex_variant():

	dict_field = Dict( key_type=TextLine(), value_type=TextLine() )
	string_field = Object(IUnicode)
	list_of_numbers_field = ListOrTuple( value_type=Number() )

	variant = Variant( (dict_field, string_field, list_of_numbers_field) )

	# It takes all these things
	for d in { 'k': 'v'}, 'foo', [1, 2, 3]:
		assert_that( d, validated_by( variant ) )

	# It rejects these
	for d in {'k': 1}, b'foo', [1, 2, 'b']:
		assert_that( d, not_validated_by( variant ) )

from zope.component import eventtesting
from zope.testing import cleanup
from nose.tools import with_setup

@with_setup( setup=eventtesting.setUp, teardown=cleanup.cleanUp )
def test_nested_variants():
	# Use case: Chat messages are either a Dict, or a Note-like body, which itself is a list of variants

	dict_field = Dict( key_type=TextLine(), value_type=TextLine() )

	string_field = Object(IUnicode)
	number_field = Number()
	list_of_strings_or_numbers = ListOrTuple( value_type=Variant( (string_field, number_field) ) )

	assert_that( [1, '2'], validated_by( list_of_strings_or_numbers ) )
	assert_that( {'k': 'v'}, validated_by( dict_field ) )

	dict_or_list = Variant( ( dict_field, list_of_strings_or_numbers ) )

	assert_that( [1, '2'], validated_by( dict_or_list ) )
	assert_that( {'k': 'v'}, validated_by( dict_or_list ) )


	class X(object):
		pass
	x = X()
	dict_or_list.set( x, [1, '2'] )

	events = eventtesting.getEvents( IBeforeSequenceAssignedEvent )
	assert_that( events, has_length( 1 ) )
	assert_that( events, contains( has_property( 'object', [1, '2'] ) ) )

	eventtesting.clearEvents()

	dict_or_list.set( x, {'k': 'v'} )
	events = eventtesting.getEvents( IBeforeDictAssignedEvent )
	assert_that( events, has_length( 1 ) )
	assert_that( events, contains( has_property( 'object', {'k': 'v'} ) ) )


def test_objectlen():
	# If we have the inheritance messed up, we will have problems
	# creating, or we will have problems validating one part or the other.

	olen = ObjectLen( IUnicode, max_length=5 ) # default val for min_length

	olen.validate( 'a' )
	olen.validate( '' )

	with assert_raises( sch_interfaces.SchemaNotProvided ):
		olen.validate( object() )

	with assert_raises( sch_interfaces.TooLong ):
		olen.validate( 'abcdef' )
