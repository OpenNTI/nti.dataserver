from . import ConfiguringTestBase, EmptyMockDocument, NoPhantomRenderedBook
from nti.contentrendering import sectionvideoadder
from nti.tests import provides
from nti.contentrendering import interfaces

import os
import tempfile
import shutil
from hamcrest import assert_that, is_, same_instance


def test_class_provides():
	assert_that( sectionvideoadder.YouTubeRelatedVideoAdder, provides(interfaces.IStaticYouTubeEmbedVideoAdder ) )

class _AbstractSectionTransformer(ConfiguringTestBase):

	base_path = None
	video_path = None
	expected_video_count = 0

	def setUp(self):
		super(_AbstractSectionTransformer,self).setUp()
		temp_d = tempfile.mkdtemp()
		base_path = os.path.join( os.path.dirname( __file__ ),  self.base_path )
		dest_d = os.path.join( temp_d, self.base_path )
		shutil.copytree( base_path, dest_d )
		self.contentLocation = dest_d
		if self.video_path:
			shutil.copy( os.path.join( os.path.dirname( __file__ ), self.video_path ), temp_d )
		self.temp_d = temp_d

	def tearDown(self):
		super(_AbstractSectionTransformer,self).tearDown()
		shutil.rmtree( self.temp_d )
		#print self.temp_d

	def test_add_videos(self):

		book = NoPhantomRenderedBook( EmptyMockDocument(), self.contentLocation )
		result = sectionvideoadder.performTransforms( book )
		util, count = result[0]
		assert_that( util, is_( same_instance( sectionvideoadder.YouTubeRelatedVideoAdder ) ) )
		assert_that( count, is_( self.expected_video_count ) )


class TestSectionTransforms(_AbstractSectionTransformer):
	"""
	Tests the earlier functionality, using simple, hard-coded replacements.
	"""
	base_path = 'sectionvideoadder'
	video_path = 'nti-youtube-embedded-section-videos.txt'
	expected_video_count = 110

class TestConfiguredSelectorTransforms(_AbstractSectionTransformer):
	"""
	Tests that newer, configured replacements happen as expected, including
	changing the selector and using an NTIID
	"""
	base_path = 'mathcountssectionvideoadder'
	video_path = base_path + '/' + TestSectionTransforms.video_path
	expected_video_count = 4
