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
from hamcrest import none
from hamcrest import has_key
from hamcrest import has_entry
from nose.tools import assert_raises

import nti.tests

from nti.zodb.urlproperty import UrlProperty

import zope.schema.interfaces

def test_getitem():

	prop = UrlProperty()

	getter = prop.make_getitem()

	with assert_raises( KeyError ):
		getter( object(), 'foobar' )

	assert_that( getter( object(), prop.data_name ), is_( none() ) )


def test_delete():

	prop = UrlProperty()

	assert_that( prop.__delete__( None ), is_( none() ) )

	class O(object):
		pass

	o = O()
	setattr( o, prop.url_attr_name, 1 )
	setattr( o, prop.file_attr_name, 2 )

	prop.__delete__( o )

	assert_that( o.__dict__, is_( {} ) )

def test_reject_url_with_missing_host():

	prop = UrlProperty()

	prop.reject_url_with_missing_host = True

	class O(object):
		pass
	with assert_raises(zope.schema.interfaces.InvalidURI):
		prop.__set__( O(), '/path/to/thing' )
