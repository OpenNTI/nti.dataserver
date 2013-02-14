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

from nti.utils.schema import HTTPURL
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
