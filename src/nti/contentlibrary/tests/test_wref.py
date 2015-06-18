#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import os

from zope import component

try:
	from six.moves import cPickle as pickle
except ImportError:
	import pickle

from nti.contentlibrary import filesystem
from nti.contentlibrary import interfaces
from nti.contentlibrary.wref import ContentUnitWeakRef
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.wref.interfaces import IWeakRef

from nti.contentlibrary.tests import ContentlibraryLayerTest

class TestWref(ContentlibraryLayerTest):

	def setUp(self):
		global_library = self.global_library = filesystem.GlobalFilesystemContentPackageLibrary( os.path.dirname(__file__) )
	
		global_library.syncContentPackages()

		component.getGlobalSiteManager().registerUtility( global_library,
														  provided=IContentPackageLibrary )

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.global_library,
															provided=IContentPackageLibrary )


	def test_wref(self):
		lib = component.getUtility(interfaces.IContentPackageLibrary)

		unit = lib['tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.']

		wref = IWeakRef(unit)

		assert_that( wref(), is_( unit ))

		wref2 = pickle.loads( pickle.dumps(wref) )

		assert_that( wref2, is_( wref ))

		assert_that( wref2(), is_( unit ))

	def test_wref_to_persistent(self):
		unit = filesystem.PersistentFilesystemContentUnit()
		unit.ntiid = 'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.'

		wref = IWeakRef(unit)

		assert_that( wref, is_(ContentUnitWeakRef))

		# It resolves to what's in the library
		lib = component.getUtility(interfaces.IContentPackageLibrary)

		lib_unit = lib['tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california.']

		wref = IWeakRef(unit)

		assert_that( wref(), is_( lib_unit ))
