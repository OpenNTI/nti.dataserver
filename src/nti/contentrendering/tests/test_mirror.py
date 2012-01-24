#!/usr/bin/env python2.7
from . import ConfiguringTestBase
from nti.contentrendering import mirror


import os
from hamcrest import assert_that, has_item, is_not, contains_string, has_length, is_
import tempfile
import shutil



class TestMirror(ConfiguringTestBase):

	_TO_SAVE = ('_execute_cmd', '_launch_server', '_get_toc_file')

	def setUp(self):
		self.saved = []
		for name in self._TO_SAVE:
			self.saved.append( getattr( mirror, name ) )

		self.temp_dir = tempfile.mkdtemp()
		super(TestMirror,self).setUp()

	def tearDown(self):
		for name, func in zip(self._TO_SAVE, self.saved):
			setattr( mirror, name, func )

		shutil.rmtree( self.temp_dir )

	def test_mirror_includes_video_excludes_fragments(self):
		" Mirrored files should include vides, but not anything with a fragment. "
		fetched_urls = []
		parent_dirs = set()
		def execute_fetch(arg):
			# This is pretty fragile. We're depending on the way we construct the
			# command string we use for wget.
			path = arg[-1][len('http://localhost:7777/'):]
			fetched_urls.append( path )
			for p in arg:
				if p.startswith( '-P' ):
					parent_dirs.add( p )
			return True
		class MockServer(object):
			def shutdown(self): pass
			def server_close(self): pass
		def launch( url_or_path, port ):
			return MockServer()

		def get_toc(url, archive_dir):
			shutil.copy( os.path.join( os.path.dirname(__file__), 'mirror_video_base', 'eclipse-toc.xml' ),
						 archive_dir )
			return True


		mirror._execute_cmd = execute_fetch
		mirror._launch_server = launch
		mirror._get_toc_file = get_toc

		assert_that( os.path.exists('archive.zip'), is_( False ) )
		mirror.main( os.path.join( os.path.dirname(__file__), 'mirror_video_base' ),
					 self.temp_dir, )
		# There should now be an archive file. (Verifying the contents is a bit harder)
		assert_that( os.path.exists('archive.zip'), is_( True ) )
		os.remove( 'archive.zip' )

		# The video and the thumbnail
		assert_that( fetched_urls, has_item('videos/addition-1.small.m4v') )
		assert_that( fetched_urls, has_item('icons/videos/addition-1.png') )
		# always fetched to the same root
		assert_that( parent_dirs, has_length( 1 ) )
		# No fragments
		assert_that( fetched_urls, is_not( has_item( contains_string( '#' ) ) ) )
		# And it's a set
		fetched_urls.sort()
		assert_that( fetched_urls, has_length( len(set( fetched_urls )) ) )

