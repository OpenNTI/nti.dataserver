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
from hamcrest import has_entry
from nose.tools import assert_raises

import nti.tests

from nti.utils.schema import HTTPURL, ObjectOr, ObjectLen, Object
from dolmen.builtins import IUnicode
from zope.interface.common import interfaces as cmn_interfaces
from zope.schema import interfaces as sch_interfaces
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



def test_objector( ):

	syntax_or_lookup = ObjectOr( (Object(cmn_interfaces.ISyntaxError),Object(cmn_interfaces.ILookupError), Object(IUnicode)) )

	# validates
	syntax_or_lookup.validate( SyntaxError() )
	syntax_or_lookup.validate( LookupError() )

	# doesn't validate
	with assert_raises( sch_interfaces.ValidationError ):
		syntax_or_lookup.validate( b'foo' )


	assert_that( syntax_or_lookup.fromObject( 'foo' ), is_( 'foo' ) )

	with assert_raises( TypeError ):
		syntax_or_lookup.fromObject( object() )

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
