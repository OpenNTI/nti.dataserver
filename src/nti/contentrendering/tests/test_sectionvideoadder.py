#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import same_instance

import os
import shutil
import tempfile

from nti.contentrendering import interfaces
from nti.contentrendering import sectionvideoadder
from nti.contentrendering.utils import EmptyMockDocument, NoPhantomRenderedBook
from nti.testing.matchers import provides
from nti.contentrendering.tests import ContentrenderingLayerTest



class _AbstractSectionTransformer(object):

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


	def test_class_provides(self):
		assert_that( sectionvideoadder.YouTubeRelatedVideoAdder, provides(interfaces.IStaticYouTubeEmbedVideoAdder ) )


	def test_add_videos(self):

		book = NoPhantomRenderedBook( EmptyMockDocument(), self.contentLocation )
		result = sectionvideoadder.performTransforms( book )
		util, count = result[0]
		assert_that( util, is_( same_instance( sectionvideoadder.YouTubeRelatedVideoAdder ) ) )
		assert_that( count, is_( self.expected_video_count ) )


class TestSectionTransforms(_AbstractSectionTransformer, ContentrenderingLayerTest):
	"""
	Tests the earlier functionality, using simple, hard-coded replacements.
	"""
	base_path = 'sectionvideoadder'
	video_path = 'nti-youtube-embedded-section-videos.txt'
	expected_video_count = 110

class TestConfiguredSelectorTransforms(_AbstractSectionTransformer,ContentrenderingLayerTest):
	"""
	Tests that newer, configured replacements happen as expected, including
	changing the selector and using an NTIID
	"""
	base_path = 'mathcountssectionvideoadder'
	video_path = base_path + '/' + TestSectionTransforms.video_path
	expected_video_count = 4
