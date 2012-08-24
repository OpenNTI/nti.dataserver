from . import ConfiguringTestBase
from nti.contentrendering import RenderedBook
from nti.contentrendering import default_root_sharing_setter
from nti.tests import provides
from nti.contentrendering import interfaces

import io
import os
import shutil
from hamcrest import assert_that, has_entry, has_item, has_property, has_length, greater_than_or_equal_to, is_, is_not, none

TEST_CONTENT = 'NextThoughtGenericTutorial-rendered-book'

def test_module_provides():
	assert_that( default_root_sharing_setter, provides(interfaces.IRenderedBookTransformer ) )

class TestTransforms(ConfiguringTestBase):

	def test_transform(self):
		"""
		Verify that defaultsharingsetter can read the default sharing info from the designated file and
		update the ToC.
		"""

		# Read the reference data
		refData = ''
		with io.open(os.path.join( os.path.dirname( __file__ ), 'nti-default-root-sharing-group.txt' ) ) as file:
			for line in file.readlines():
                                refData = ' '.join([refData, line.strip()])
			refData = refData.strip()

		# Open the copy of the rendered book
		book = RenderedBook.RenderedBook( None, os.path.join( os.path.dirname( __file__ ), TEST_CONTENT ) )

		# Assert ToC is present
		assert_that( book, has_property( 'toc', is_not( none() ) ) )
		# Assert that the root topic is present
		assert_that( book.toc, has_property( 'root_topic', is_not( none() ) ) )
		
		default_root_sharing_setter.transform( book, save_toc=False )
			
		# Assert that the shareWith property of the ToC root element is set correctly
		assert_that( book.toc.root_topic.get_default_sharing_group(), is_( refData ) )
