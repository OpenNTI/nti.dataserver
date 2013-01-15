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
from hamcrest import none
from hamcrest import same_instance
from hamcrest import has_property

from nti.contentlibrary import externalization
from nti.contentlibrary import interfaces

from zope import interface
from zope import component

from ..boto_s3 import BotoS3ContentUnit
from ..boto_s3 import _read_key as read_key

from cStringIO import StringIO
import gzip

from nti.tests import ConfiguringTestBase

class TestBotoCDNKeyMapper(ConfiguringTestBase):
	set_up_packages = ('nti.externalization', 'nti.contentlibrary')

	def test_does_exist_cached(self):
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


	def test_key_mapper(self):
		class Bucket(object):
			name = None
			def get_key( self, k ):
				return object()

		@interface.implementer(interfaces.IS3Key)
		class Key(object):
			bucket = None
			key = None

			def __init__( self, bucket=None, key=None ):
				if bucket: self.bucket = bucket
				if key: self.key = key

		bucket = Bucket()
		bucket.name = 'content.nextthought.com'
		key = Key( bucket, 'mathcounts2012/index.html' )

		# by default we assume the bucket
		assert_that( component.getAdapter( key, interfaces.IAbsoluteContentUnitHrefMapper ),
					 has_property( 'href', 'http://content.nextthought.com/mathcounts2012/index.html' ) )

		# but we can replace that...
		externalization.map_all_buckets_to( 'test_key_mapper.cloudfront.amazon.com' )

		assert_that( interfaces.IAbsoluteContentUnitHrefMapper( key ),
					 has_property( 'href', '//test_key_mapper.cloudfront.amazon.com/mathcounts2012/index.html' ) )


	def test_read_contents( self ):
		class Key(object):
			bucket = None
			name = None
			contents = ''
			content_encoding = None

			def __init__( self, bucket=None, name=None ):
				if bucket: self.bucket = bucket
				if name: self.name = name

			def get_contents_as_string(self):
				return self.contents

		assert_that( read_key( None ), is_( none() ) )
		assert_that( read_key( Key() ), is_( '' ) )

		key = Key()
		key.content_encoding = 'gzip'
		strio = StringIO()
		gzipped = gzip.GzipFile( fileobj=strio, mode='wb' )
		gzipped.write( 'The contents' )
		gzipped.close()
		data = strio.getvalue()
		key.contents = data

		assert_that( read_key( key ), is_( 'The contents' ) )
