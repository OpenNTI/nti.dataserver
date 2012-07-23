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
from nti.tests import verifiably_provides, ConfiguringTestBase

from nti.contentlibrary import contentunit, interfaces

class TestFilesystemContentUnit(ConfiguringTestBase):

	def test_filesystem_content_interfaces(self):

		unit = contentunit.FilesystemContentPackage(
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

		unit = contentunit.FilesystemContentPackage(
			filename='prealgebra/index.html',
			href = 'index.html',
			root = 'prealgebra',
			icon = 'icons/The%20Icon.png' )

		assert_that( IPrefs( unit, None ), is_( none() ) )

		unit.sharedWith = ['foo']

		assert_that( IPrefs( unit ), verifiably_provides( IPrefs ) )
		assert_that( IPrefs( unit ), has_property( '__parent__', unit ) )
