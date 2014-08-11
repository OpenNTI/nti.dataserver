#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not
from hamcrest import same_instance
from hamcrest import has_length

from nti.testing import base
from nti.testing import matchers

import os

from zope import component

from nti.wref.interfaces import IWeakRef

from ..interfaces import IContentPackageLibrary
from .. import filesystem
from .. import interfaces

from ..wref import ContentUnitWeakRef

from . import ContentlibraryLayerTest

from six.moves import cPickle as pickle

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
