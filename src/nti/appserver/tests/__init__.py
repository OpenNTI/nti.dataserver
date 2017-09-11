#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import gc
import nti.appserver

import zope.deferredimport
zope.deferredimport.initialize()

import nti.base.deprecation  # Increase warning verbosity

from nti.app.testing.testing import TestMailDelivery
from nti.app.testing.testing import ITestMailDelivery

from nti.app.testing.matchers import has_permission as _has_permission
from nti.app.testing.matchers import doesnt_have_permission as _doesnt_have_permission

from nti.app.testing.request_response import DummyRequest

from nti.app.testing.base import _create_request
_create_request = _create_request

from nti.app.testing.base import TestBaseMixin
_TestBaseMixin = TestBaseMixin

from nti.app.testing.base import ConfiguringTestBase
ConfiguringTestBase = ConfiguringTestBase

from nti.app.testing.base import SharedConfiguringTestBase
SharedConfiguringTestBase = SharedConfiguringTestBase

from nti.app.testing.base import NewRequestSharedConfiguringTestBase
NewRequestSharedConfiguringTestBase = NewRequestSharedConfiguringTestBase

import os
import os.path

from zope import component

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.app.testing.application_webtest import ApplicationTestLayer

class ExLibraryApplicationTestLayer(ApplicationTestLayer):
	library_dir = os.path.join(os.path.dirname(__file__), 'ExLibrary')
	@classmethod
	def _setup_library(cls, *args, **kwargs):
		from nti.contentlibrary.filesystem import EnumerateOnceFilesystemLibrary as FileLibrary
		return FileLibrary(cls.library_dir)

	@classmethod
	def setUp(cls):
		# Must implement!
		gsm = component.getGlobalSiteManager()
		cls.__old_library = gsm.queryUtility(IContentPackageLibrary)
		if cls.__old_library is not None:
			cls.__old_library.resetContentPackages()

		lib = cls._setup_library()

		gsm.registerUtility(lib, IContentPackageLibrary)
		lib.syncContentPackages()
		cls.__current_library = lib

	@classmethod
	def tearDown(cls):
		# Must implement!
		gsm = component.getGlobalSiteManager()
		cls.__current_library.resetContentPackages()
		gsm.unregisterUtility(cls.__current_library, IContentPackageLibrary)
		del cls.__current_library
		if cls.__old_library is not None:
			gsm.registerUtility(cls.__old_library, IContentPackageLibrary)
			# XXX Why would we need to sync the content packages here? It's been
			# sidelined this whole time. Doing so leads to InappropriateSiteError
			#cls.__old_library.syncContentPackages()

		del cls.__old_library
		gc.collect()

	# TODO: May need to recreate the application with this library?

	@classmethod
	def testSetUp(cls):
		# must implement!
		pass

	@classmethod
	def testTearDown(cls):
		# must implement!
		pass
