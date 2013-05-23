#!/usr/bin/env python
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import not_none
from hamcrest import has_length


from hamcrest import is_not
does_not = is_not

from nti.tests import validly_provides
import os
import os.path


from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary
from nti.contentlibrary import interfaces as lib_interfaces
from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentprocessing.metadata_extractors import get_metadata_from_content_location

from nti.dataserver import authorization as nauth

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS
from nti.appserver.traversal import find_interface

class TestApplicationMetadataResolvers(SharedApplicationTestBase):
	child_ntiid =  b'tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.history_and_career_opportuniities'

	@classmethod
	def _setup_library( cls, *args, **kwargs ):
		return FileLibrary( os.path.join( os.path.dirname(__file__), 'ExLibrary' ) )



	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_metadata_from_ntiid(self):
		metadata = get_metadata_from_content_location( self.child_ntiid )

		assert_that( metadata, validly_provides( cp_interfaces.IContentMetadata ) )
		assert_that( metadata.images, has_length( 1 ) )

		# The lineage to do ACLs is intact
		assert_that( find_interface( metadata, lib_interfaces.IContentPackage), is_( not_none() ) )
