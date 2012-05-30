#!/usr/bin/env python
from hamcrest import assert_that, has_entry



from nti.contentlibrary import externalization
from nti.contentlibrary import contentunit



def test_doesnt_dual_escape():
	unit = contentunit.FilesystemContentPackage(
		filename='prealgebra/index.html',
		href = 'index.html',
		root = 'prealgebra',
		icon = 'icons/The%20Icon.png' )

	assert_that( externalization._ContentPackageExternal(unit).toExternalObject(),
				 has_entry( 'icon', '/prealgebra/icons/The%20Icon.png' ) )


def test_escape_if_needed():
	unit = contentunit.FilesystemContentPackage(
		filename='prealgebra/index.html',
		href = 'index.html',
		root = 'prealgebra',
		icon = 'icons/The Icon.png' )

	assert_that( externalization._ContentPackageExternal(unit).toExternalObject(),
				 has_entry( 'icon', '/prealgebra/icons/The%20Icon.png' ) )

	assert_that( externalization._ContentPackageExternal(unit).toExternalObject(),
				 has_entry( 'renderVersion', 1 ) )
