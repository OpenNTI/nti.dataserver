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

class TestTransforms(ConfiguringTestBase):

	def setUp(self):
		super(TestTransforms,self).setUp()
		temp_d = tempfile.mkdtemp()
		base_path = os.path.join( os.path.dirname( __file__ ),  'sectionvideoadder' )
		dest_d = os.path.join( temp_d, 'sectionvideoadder' )
		shutil.copytree( base_path, dest_d )
		self.contentLocation = dest_d
		shutil.copy( os.path.join( os.path.dirname( __file__ ), 'nti-youtube-embedded-section-videos.txt' ), temp_d )
		self.temp_d = temp_d

	def tearDown(self):
		super(TestTransforms,self).tearDown()
		shutil.rmtree( self.temp_d )
		#print self.temp_d

	def test_add_videos(self):

		book = NoPhantomRenderedBook( EmptyMockDocument(), self.contentLocation )
		result = sectionvideoadder.performTransforms( book )
		util, count = result[0]
		assert_that( util, is_( same_instance( sectionvideoadder.YouTubeRelatedVideoAdder ) ) )
		assert_that( count, is_( 110 ) )
