#!/usr/bin/env python
from hamcrest import assert_that, has_entry, has_entries
from hamcrest import greater_than_or_equal_to
from hamcrest import has_key
from hamcrest import is_not
from hamcrest import is_

from nti.contentlibrary import filesystem, boto_s3

import nti.tests
import nti.contentlibrary
import nti.externalization

from nti.externalization.interfaces import IExternalObject

# Nose module-level setup and teardown
#setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.contentlibrary,nti.externalization) )
#tearDownModule = nti.tests.module_teardown

# def setUpModule():
# 	print("Setting up", __name__ )
# 	nti.tests.module_setup( set_up_packages=(nti.contentlibrary,nti.externalization) )

# def tearDownModule():
# 	print("Tearing down", __name__ )
# 	nti.tests.module_teardown()

from nti.tests import ConfiguringTestBase
import boto.s3.bucket
import boto.s3.key
import fudge

class TestExternalization(ConfiguringTestBase):
	set_up_packages = (nti.contentlibrary, nti.externalization )

	def test_doesnt_dual_escape(self):
		unit = filesystem.FilesystemContentPackage(
			filename='prealgebra/index.html',
			href = 'index.html',
			root = 'prealgebra',
			icon = 'icons/The%20Icon.png' )

		assert_that( IExternalObject(unit).toExternalObject(),
					 has_entry( 'icon', '/prealgebra/icons/The%20Icon.png' ) )


	def _do_test_escape_if_needed( self, factory, key, index='eclipse-toc.xml', archive_unit=None, prefix='', installable=True):
		unit = factory(
			key=key,
			href = 'index.html',
			root = 'prealgebra',
			icon = 'icons/The Icon.png',
			title = 'Prealgebra',
			installable = archive_unit is not None,
			archive_unit = archive_unit,
			index = index )

		if archive_unit:
			unit.archive_unit.__parent__ = unit

		result = IExternalObject( unit ).toExternalObject()
		assert_that( result,
					 has_entry( 'icon', prefix + '/prealgebra/icons/The%20Icon.png' ) )

		assert_that( result, has_key( 'index_jsonp' ) )
		assert_that( result,
					 has_entry( 'renderVersion', 1 ) )
		assert_that( result, has_entry( 'Class', 'ContentPackage' ) )

		# More coverage
		assert_that( result,
					 has_entries( 'DCCreator', (),
								  'DCTitle', 'Prealgebra',
								  'Last Modified', greater_than_or_equal_to( 0 ),
								  'index', prefix + '/prealgebra/eclipse-toc.xml',
								  'root', prefix + '/prealgebra/',
								  'archive', prefix + '/prealgebra/archive.zip',
								  'version', '1.0',
								  'installable', installable ) )
		return unit

	def test_escape_if_needed_filesystem_rel_path(self):
		def factory(**kwargs):
			r = filesystem.FilesystemContentPackage(**kwargs)
			r.index = r.make_sibling_key( 'eclipse-toc.xml' )
			return r
		self._do_test_escape_if_needed(
			factory,
			key='prealgebra/index.html',
			index=None,
			archive_unit=filesystem.FilesystemContentUnit( filename='archive.zip', href='archive.zip' ) )

	def test_escape_if_needed_filesystem_full_path(self):
		def factory(**kwargs):
			r = filesystem.FilesystemContentPackage(**kwargs)
			r.index = r.make_sibling_key( 'eclipse-toc.xml' )
			return r

		self._do_test_escape_if_needed( factory,
										index=None,
										key='/DNE/Library/WebServer/Documents/prealgebra/index.html',
										archive_unit=filesystem.FilesystemContentUnit( filename='archive.zip', href='archive.zip' ),
										installable=True	)




	@fudge.patch('nti.contentlibrary.boto_s3.BotoS3ContentUnit._connect_key')
	def test_escape_if_needed_boto(self, fake_connect):
		fake_connect.expects_call()
		bucket = boto_s3.NameEqualityBucket(name='content.nextthought.com')
		key = bucket.key_class( bucket=bucket, name='prealgebra/index.html' )
		key.last_modified = 0
		index = bucket.key_class( bucket=bucket, name='prealgebra/eclipse-toc.xml' )

		assert_that( key, is_not( index ) )
		assert_that( key, is_( key ) )
		assert_that( bucket, is_( bucket ) )
		d = { key: index }
		key2 = bucket.key_class( bucket=bucket, name='prealgebra/index.html' )
		assert_that( d.get( key2 ), is_( index ) )

		self._do_test_escape_if_needed( boto_s3.BotoS3ContentPackage, key=key, index=index, prefix='http://content.nextthought.com',
								  archive_unit=boto_s3.BotoS3ContentUnit( key=boto.s3.key.Key( bucket=bucket, name='prealgebra/archive.zip' ) ),
								  installable=True	)
