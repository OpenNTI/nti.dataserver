#!/usr/bin/env python
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import contains
from hamcrest import is_not
does_not = is_not

from nti.testing.matchers import validly_provides
import os
import os.path


from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary
from nti.contentlibrary import interfaces as lib_interfaces
from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentprocessing.metadata_extractors import get_metadata_from_content_location


from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS
from . import ExLibraryApplicationTestLayer

from nti.appserver.traversal import find_interface

class TestApplicationMetadataResolvers(ApplicationLayerTest):
	layer = ExLibraryApplicationTestLayer
	child_ntiid =  b'tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.history_and_career_opportuniities'


	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_metadata_from_ntiid(self):
		metadata = get_metadata_from_content_location( self.child_ntiid )
		assert_that( metadata, validly_provides( cp_interfaces.IContentMetadata ) )
		# The URLs are properly mapped
		assert_that( metadata, has_property( 'contentLocation',
											 '/WithAssessment/tag_nextthought_com_2011-10_MN-HTML-MiladyCosmetology_history_and_career_opportuniities.html' ) )
		# Both a manual icon and a thumbnail are found
		assert_that( metadata.images, has_length( 2 ) )
		assert_that( metadata.images, contains( has_property( 'url',
															  '/WithAssessment/icons/chapters/C1.png' ),
												has_property( 'url',
															  '/WithAssessment/thumbnails/tag_nextthought_com_2011-10_MN-HTML-MiladyCosmetology_history_and_career_opportuniities.png' ) ) )


		# The lineage to do ACLs is intact
		assert_that( find_interface( metadata, lib_interfaces.IContentPackage), is_( not_none() ) )
