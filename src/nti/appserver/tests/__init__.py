import nti.appserver

import zope.deferredimport
zope.deferredimport.initialize()


import nti.deprecated # Increase warning verbosity
assert nti.deprecated
from nti.app.testing.request_response import DummyRequest
from nti.app.testing.testing import TestMailDelivery
from nti.app.testing.testing import ITestMailDelivery


from nti.app.testing.matchers import has_permission as _has_permission
from nti.app.testing.matchers import doesnt_have_permission as _doesnt_have_permission

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

from zope import component
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.app.testing.application_webtest import ApplicationTestLayer
import os
import os.path

class ExLibraryApplicationTestLayer(ApplicationTestLayer):
	library_dir = os.path.join( os.path.dirname(__file__), 'ExLibrary' )
	@classmethod
	def _setup_library( cls, *args, **kwargs ):
		from nti.contentlibrary.filesystem import EnumerateOnceFilesystemLibrary as FileLibrary
		return FileLibrary( cls.library_dir )

	@classmethod
	def setUp(cls):
		# Must implement!
		cls.__old_library = component.getUtility(IContentPackageLibrary)
		cls.__old_library.resetContentPackages()

		lib = cls._setup_library()

		component.provideUtility(lib, IContentPackageLibrary)
		lib.syncContentPackages()
		cls.__current_library = lib

	@classmethod
	def tearDown(cls):
		# Must implement!
		cls.__current_library.resetContentPackages()
		del cls.__current_library
		component.provideUtility(cls.__old_library, IContentPackageLibrary)
		cls.__old_library.syncContentPackages()

	# TODO: May need to recreate the application with this library?

	@classmethod
	def testSetUp(cls):
		# must implement!
		pass

	@classmethod
	def testTearDown(cls):
		# must implement!
		pass
