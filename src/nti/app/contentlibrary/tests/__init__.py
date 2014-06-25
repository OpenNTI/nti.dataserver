#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import component
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.app.testing.application_webtest import ApplicationTestLayer
import os
import os.path

from nti.contentlibrary.filesystem import EnumerateOnceFilesystemLibrary as FileLibrary
from nti.contentlibrary.bundle import ContentPackageBundleLibrary
from nti.contentlibrary.interfaces import ISyncableContentPackageBundleLibrary
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary

class _SharedSetup(object):

	@staticmethod
	def _setup_library( cls, *args, **kwargs ):
		return FileLibrary( cls.library_dir )

	@staticmethod
	def setUp(cls):
		# Must implement!
		cls.__old_library = component.getUtility(IContentPackageLibrary)
		global_library = cls.global_library = cls._setup_library()

		component.provideUtility(global_library, IContentPackageLibrary)
		global_library.syncContentPackages()

		# XXX: This duplicates a lot of what's done by subscribers
		# in nti.contentlibrary

		global_bundle_library = ContentPackageBundleLibrary()
		cls.bundle_library = global_bundle_library
		component.provideUtility(global_bundle_library, IContentPackageBundleLibrary)

		bucket = global_library._enumeration.root.getChildNamed('sites').getChildNamed('localsite').getChildNamed('ContentPackageBundles')
		ISyncableContentPackageBundleLibrary(global_bundle_library).syncFromBucket(bucket)

	@staticmethod
	def tearDown(cls):
		# Must implement!
		component.provideUtility(cls.__old_library, IContentPackageLibrary)

		component.getGlobalSiteManager().unregisterUtility(cls.bundle_library, IContentPackageBundleLibrary)


class CourseTestContentApplicationTestLayer(ApplicationTestLayer):
	library_dir = os.path.join( os.path.dirname(__file__), 'library' )

	@classmethod
	def _setup_library( cls, *args, **kwargs ):
		return _SharedSetup._setup_library(cls)

	@classmethod
	def setUp(cls):
		# Must implement!
		_SharedSetup.setUp(cls)

	@classmethod
	def tearDown(cls):
		_SharedSetup.tearDown(cls)
		# Must implement!


	# TODO: May need to recreate the application with this library?

import nti.contentlibrary.tests

class ContentLibraryApplicationTestLayer(ApplicationTestLayer):
	library_dir = os.path.join( os.path.dirname(nti.contentlibrary.tests.__file__) )
	@classmethod
	def _setup_library( cls, *args, **kwargs ):
		return _SharedSetup._setup_library(cls)

	@classmethod
	def setUp(cls):
		# Must implement!
		_SharedSetup.setUp(cls)

	@classmethod
	def tearDown(cls):
		_SharedSetup.tearDown(cls)
		# Must implement!

	# TODO: May need to recreate the application with this library?
