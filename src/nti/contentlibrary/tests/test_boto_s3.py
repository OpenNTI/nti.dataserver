#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import same_instance

from ..boto_s3 import BotoS3ContentUnit

def test_does_exist_cached():
	class Bucket(object):
		def get_key( self, k ):
			return object()

	class Key(object):
		bucket = None
		name = None

		def __init__( self, bucket=None, name=None ):
			if bucket: self.bucket = bucket
			if name: self.name = name

	key = Key()
	key.name = 'foo/bar'
	key.bucket = Bucket()
	unit = BotoS3ContentUnit( key=key )

	assert_that( unit.does_sibling_entry_exist( 'baz' ), is_( not_none() ) )
	assert_that( unit.does_sibling_entry_exist( 'baz' ), is_( same_instance( unit.does_sibling_entry_exist( 'baz' ) ) ) )

	assert_that( unit.does_sibling_entry_exist( 'bar' ), is_not( same_instance( unit.does_sibling_entry_exist( 'baz' ) ) ) )
