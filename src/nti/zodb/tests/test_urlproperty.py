#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that

import unittest

import zope.schema.interfaces

from nti.zodb.urlproperty import UrlProperty

from nose.tools import assert_raises

class TestURLProperty(unittest.TestCase):
	
	def test_getitem(self):
		prop = UrlProperty()
		getter = prop.make_getitem()
	
		with assert_raises( KeyError ):
			getter( object(), 'foobar' )
		assert_that( getter( object(), prop.data_name ), is_( none() ) )
	
	def test_delete(self):
		prop = UrlProperty()
		assert_that( prop.__delete__( None ), is_( none() ) )
	
		class O(object):
			pass
	
		o = O()
		setattr( o, prop.url_attr_name, 1 )
		setattr( o, prop.file_attr_name, 2 )
	
		prop.__delete__( o )
		assert_that( o.__dict__, is_( {} ) )
	
	def test_reject_url_with_missing_host(self):
		prop = UrlProperty()
		prop.reject_url_with_missing_host = True
	
		class O(object):
			pass
		with assert_raises(zope.schema.interfaces.InvalidURI):
			prop.__set__( O(), '/path/to/thing' )
