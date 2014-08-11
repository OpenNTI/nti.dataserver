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
from hamcrest import has_key
from hamcrest import greater_than
from hamcrest import has_property

from nti.testing.time import time_monotonically_increases
import os

from zope import component

from .. import filesystem
from ..interfaces import IContentPackageLibrary
from . import ContentlibraryLayerTest

from ..bundle import PersistentContentPackageBundle
from ..bundle import _ContentBundleMetaInfo
from ..bundle import sync_bundle_from_json_key

class TestBundle(ContentlibraryLayerTest):

	def setUp(self):
		global_library = self.global_library = filesystem.GlobalFilesystemContentPackageLibrary( os.path.dirname(__file__) )
		global_library.syncContentPackages()

		component.getGlobalSiteManager().registerUtility( global_library,
														  provided=IContentPackageLibrary )

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.global_library,
															provided=IContentPackageLibrary )

	@time_monotonically_increases
	def test_sync_bundle_from_meta(self):
		bucket = filesystem.FilesystemBucket()
		bucket.absolute_path = os.path.join( os.path.dirname(__file__),
										  'sites', 'localsite',
										  'ContentPackageBundles', 'ABundle')
		bucket.name = 'ABundle'
		key = bucket.getChildNamed('bundle_meta_info.json')

		bundle = PersistentContentPackageBundle()
		bundle.lastModified = -1
		bundle.createdTime = -1

		meta = _ContentBundleMetaInfo(key, self.global_library)
		meta.lastModified = -1

		sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
		lm = bundle.lastModified

		# Nothing should change now
		sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
		assert_that( bundle, has_property('lastModified', lm))

		# removing packages
		del meta._ContentPackages_wrefs
		sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
		assert_that( bundle, has_property('lastModified', greater_than(lm)))
		lm = bundle.lastModified

		# adding them back
		sync_bundle_from_json_key(key, bundle, self.global_library, _meta=meta)
		assert_that( bundle, has_property('lastModified', greater_than(lm)))
