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

class CourseTestContentApplicationTestLayer(ApplicationTestLayer):
	library_dir = os.path.join( os.path.dirname(__file__), 'library' )

	@classmethod
	def _setup_library( cls, *args, **kwargs ):
		return FileLibrary( cls.library_dir )

	@classmethod
	def setUp(cls):
		# Must implement!
		cls.__old_library = component.getUtility(IContentPackageLibrary)
		component.provideUtility(cls._setup_library(), IContentPackageLibrary)
		getattr(component.getUtility(IContentPackageLibrary), 'contentPackages')
	@classmethod
	def tearDown(cls):
		# Must implement!
		component.provideUtility(cls.__old_library, IContentPackageLibrary)

	# TODO: May need to recreate the application with this library?

import nti.contentlibrary.tests

class ContentLibraryApplicationTestLayer(ApplicationTestLayer):
	library_dir = os.path.join( os.path.dirname(nti.contentlibrary.tests.__file__) )

	@classmethod
	def _setup_library( cls, *args, **kwargs ):
		return FileLibrary( cls.library_dir )

	@classmethod
	def setUp(cls):
		# Must implement!
		cls.__old_library = component.getUtility(IContentPackageLibrary)
		component.provideUtility(cls._setup_library(), IContentPackageLibrary)
		getattr(component.getUtility(IContentPackageLibrary), 'contentPackages')
	@classmethod
	def tearDown(cls):
		# Must implement!
		component.provideUtility(cls.__old_library, IContentPackageLibrary)

	# TODO: May need to recreate the application with this library?
