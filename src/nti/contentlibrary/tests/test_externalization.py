#!/usr/bin/env python
from hamcrest import assert_that, has_entry, has_entries


from nti.contentlibrary import filesystem, boto_s3

import nti.tests
import nti.contentlibrary
import nti.externalization

from nti.externalization.interfaces import IExternalObject

# Nose module-level setup and teardown
setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.contentlibrary,nti.externalization) )
tearDownModule = nti.tests.module_teardown

def test_doesnt_dual_escape():
	unit = filesystem.FilesystemContentPackage(
		filename='prealgebra/index.html',
		href = 'index.html',
		root = 'prealgebra',
		icon = 'icons/The%20Icon.png' )

	assert_that( IExternalObject(unit).toExternalObject(),
				 has_entry( 'icon', '/prealgebra/icons/The%20Icon.png' ) )


def _do_test_escape_if_needed(factory, key, index='eclipse-toc.xml', archive_unit=None, prefix=''):
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

	assert_that( result,
				 has_entry( 'renderVersion', 1 ) )

	# More coverage
	assert_that( result,
				 has_entries( 'DCCreator', (),
							  'DCTitle', 'Prealgebra',
							  'Last Modified', 0,
							  'index', prefix + '/prealgebra/eclipse-toc.xml',
							  'root', prefix + '/prealgebra/',
							  'archive', prefix + '/prealgebra/archive.zip',
							  'version', '1.0' ) )

def test_escape_if_needed_filesystem():
	_do_test_escape_if_needed( filesystem.FilesystemContentPackage, key='prealgebra/index.html',
							  archive_unit=filesystem.FilesystemContentUnit( filename='archive.zip', href='archive.zip' ) )

import boto.s3.bucket
import boto.s3.key
import fudge

@fudge.patch('nti.contentlibrary.boto_s3.BotoS3ContentUnit._connect_key')
def test_escape_if_needed_boto(fake_connect):
	fake_connect.expects_call()
	bucket = boto.s3.bucket.Bucket(name='content.nextthought.com')
	key = boto.s3.key.Key( bucket=bucket, name='prealgebra/index.html' )
	key.last_modified = 0
	index = boto.s3.key.Key( bucket=bucket, name='prealgebra/eclipse-toc.xml' )

	_do_test_escape_if_needed( boto_s3.BotoS3ContentPackage, key=key, index=index, prefix='http://content.nextthought.com',
							  archive_unit=boto_s3.BotoS3ContentUnit( key=boto.s3.key.Key( bucket=bucket, name='prealgebra/archive.zip' ) ) )
