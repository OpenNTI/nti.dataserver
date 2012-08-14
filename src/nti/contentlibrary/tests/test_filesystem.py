#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import none
from hamcrest import has_property
from hamcrest import has_entry
from nti.tests import verifiably_provides, ConfiguringTestBase

from nti.contentlibrary import interfaces, eclipse, filesystem
import nti.contentlibrary
import nti.externalization
import nti.externalization.externalization

import anyjson as json
import os.path

class TestFilesystemContentUnit(ConfiguringTestBase):

	def test_filesystem_content_interfaces(self):

		unit = filesystem.FilesystemContentPackage(
			filename='prealgebra/index.html',
			href = 'index.html',
			root = 'prealgebra',
			icon = 'icons/The%20Icon.png' )

		assert_that( unit, verifiably_provides( interfaces.IFilesystemContentPackage ) )


	def test_adapter_prefs(self):
		import zope.dottedname.resolve as dottedname
		appserver = dottedname.resolve( 'nti.appserver' )
		IPrefs = dottedname.resolve( 'nti.appserver.interfaces.IContentUnitPreferences' )

		self.configure_packages( set_up_packages=(appserver,) )

		unit = filesystem.FilesystemContentPackage(
			filename='prealgebra/index.html',
			href = 'index.html',
			root = 'prealgebra',
			icon = 'icons/The%20Icon.png' )

		assert_that( IPrefs( unit, None ), is_( none() ) )

		unit.sharedWith = ['foo']

		assert_that( IPrefs( unit ), verifiably_provides( IPrefs ) )
		assert_that( IPrefs( unit ), has_property( '__parent__', unit ) )

	def test_from_filesystem(self):
		package = filesystem._package_factory( os.path.join( os.path.dirname( __file__ ), 'TestFilesystem' ) )
		assert_that( package.creators, is_( ('Jason',) ) )

		self.configure_packages( set_up_packages=(nti.externalization,nti.contentlibrary) )
		ext_package = nti.externalization.externalization.toExternalObject( package )
		assert_that( ext_package, has_entry( 'DCCreator', ('Jason',) ) )
		assert_that( ext_package, has_entry( 'Creator', 'Jason') )

		json.loads( json.dumps( ext_package ) ) # Round trips through JSON
