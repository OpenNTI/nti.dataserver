#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than
from hamcrest import has_property
from hamcrest import same_instance
from hamcrest import empty as is_empty
from hamcrest import is_not as does_not
from hamcrest import contains_inanyorder
from hamcrest import greater_than_or_equal_to

import time
import os.path
import anyjson as json

try:
	from six.moves import cPickle as pickle
except ImportError:
	import pickle

from zope import component
from zope.dublincore.interfaces import IWriteZopeDublinCore

from nti.contentlibrary import interfaces, filesystem

from nti.externalization.externalization import to_external_object

from nti.contentlibrary.tests import ContentlibraryLayerTest

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

class TestFilesystem(ContentlibraryLayerTest):

	def test_filesystem_content_interfaces(self):

		unit = filesystem.FilesystemContentPackage(
			#filename='prealgebra/index.html',
			href = 'index.html',
			#root = 'prealgebra',
			#icon = 'icons/The%20Icon.png'
		)

		assert_that( unit, verifiably_provides( interfaces.IFilesystemContentPackage ) )

	def test_read_contents(self):
		absolute_path = os.path.join( os.path.dirname( __file__ ),
									  'TestFilesystem' )
		bucket = filesystem.FilesystemBucket(name='TestFilesystem')
		bucket.absolute_path = absolute_path

		package = filesystem._package_factory( bucket,
											   filesystem.PersistentFilesystemContentPackage,
											   filesystem.PersistentFilesystemContentUnit)

		props = package.make_sibling_key('nti_default_presentation_properties.json')
		as_json = props.readContentsAsJson()
		as_yaml = props.readContentsAsYaml()

		assert_that(as_json, is_(as_yaml))
		assert_that(list(as_json.keys())[0],
						 is_(unicode))
		assert_that(list(as_yaml.keys())[0],
						 is_(unicode))

	def test_from_filesystem(self):
		absolute_path = os.path.join( os.path.dirname( __file__ ),
									  'TestFilesystem' )
		bucket = filesystem.FilesystemBucket(name='TestFilesystem')
		bucket.absolute_path = absolute_path

		package = filesystem._package_factory( bucket,
											   filesystem.PersistentFilesystemContentPackage,
											   filesystem.PersistentFilesystemContentUnit)
		assert_that( package.key,
					 validly_provides( interfaces.IDelimitedHierarchyKey ) )

		assert_that( package,
					 validly_provides( interfaces.IFilesystemContentPackage ) )
		assert_that( package, has_property('PlatformPresentationResources', has_length(3)))

		assert_that( package.creators, is_( ('Jason',) ) )
		# stays in sync
		zdc = IWriteZopeDublinCore(package)
		assert_that( zdc, has_property('lastModified', greater_than(0)))
		zdc.creators = ['Foo']
		assert_that( package.creators, is_( ('Foo',) ) )

		zdc.creators = ['Jason']

		assert_that( package.children[-1].children[-1],
					 has_property( 'embeddedContainerNTIIDs',
								   contains('tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1') ) )

		# The package's lastModified time is greater than the lastModified
		# of its index.html, because it's based on eclipse-toc.xml and the directory.
		# NOTE: when you change these files on disk, be sure to keep this invariant;
		# use `touch` if you have to
		assert_that( package,
					 has_property('lastModified',
								  greater_than_or_equal_to( package.key.lastModified )
						 ))

		# package pickles ok
		assert_that( pickle.loads(pickle.dumps(package)),
					 is_(package))

		ext_package = to_external_object( package )
		assert_that( ext_package, has_entry( 'DCCreator', ('Jason',) ) )
		assert_that( ext_package, has_entry( 'Creator', 'Jason') )
		assert_that( ext_package, has_entry( 'PresentationProperties',
											 is_( { 'numbering': {'suppressed': False,
																  'type': 'I',
																  'start': 5,
																  'separator': '.' } } ) ) )
		assert_that( ext_package, does_not( has_key( 'isCourse' ) ) )
		assert_that( ext_package, does_not( validly_provides( interfaces.ILegacyCourseConflatedContentPackage ) ) )

		assert_that( ext_package, has_entry( 'PlatformPresentationResources',
											 contains_inanyorder(
												 has_entry('PlatformName', 'iPad'),
												 has_entry('PlatformName', 'webapp'),
												 has_entry('PlatformName', 'shared')) ) )

		assert_that( ext_package, has_entry( 'PlatformPresentationResources',
											 contains_inanyorder(
												 has_entry('href', '/TestFilesystem/presentation-assets/iPad/v1/'),
												 has_entry('href', '/TestFilesystem/presentation-assets/webapp/v1/'),
												 has_entry('href', '/TestFilesystem/presentation-assets/shared/v1/')) ) )

		json.loads( json.dumps( ext_package ) ) # Round trips through JSON

	def test_library(self):
		library = filesystem.EnumerateOnceFilesystemLibrary( os.path.dirname(__file__) )
		library.syncContentPackages()

		assert_that( library, has_property( 'lastModified', greater_than( 0 ) ) )

		embed_paths = library.pathsToEmbeddedNTIID('tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1')
		assert_that( embed_paths, has_length( 1 ) )
		assert_that( embed_paths[0], has_length( 3 ) )
		assert_that( embed_paths[0][-1], has_property( 'ntiid', 'tag:nextthought.com,2011-10:USSC-HTML-Cohen.28' ) )

		package = library[0]

		pack_ext = to_external_object( package )
		assert_that( pack_ext, has_entry( 'href', '/TestFilesystem/index.html' ) )

		assert_that( interfaces.IContentUnitHrefMapper(package.children[0].children[0]),
					 has_property('href',
								  '/TestFilesystem/tag_nextthought_com_2011-10_USSC-HTML-Cohen_18.html#22'))

		library.url_prefix = '/SomePrefix/'

		pack_ext = to_external_object( package )
		assert_that( pack_ext, has_entry( 'href', '/SomePrefix/TestFilesystem/index.html' ) )
		assert_that( pack_ext, has_entry( 'root', '/SomePrefix/TestFilesystem/' ) )

		assert_that( interfaces.IContentUnitHrefMapper(package.children[0].children[0]),
					 has_property('href',
								  '/SomePrefix/TestFilesystem/tag_nextthought_com_2011-10_USSC-HTML-Cohen_18.html#22'))

	def test_path_to_ntiid(self):
		library = filesystem.EnumerateOnceFilesystemLibrary( os.path.dirname(__file__) )
		library.syncContentPackages()

		path1 = 'tag:nextthought.com,2011-10:USSC-HTML-Cohen.18'
		found_path = library.pathToNTIID( path1 )
		assert_that( found_path, has_length( 2 ) )

		dne_path = 'tag:nextthought.com,2011-10:USSC-HTML-Cohen.18-DoesNotExist'
		found_path = library.pathToNTIID( dne_path )
		assert_that( found_path, none() )

	def test_site_library(self):
		global_library = filesystem.GlobalFilesystemContentPackageLibrary( os.path.dirname(__file__) )
		global_library.syncContentPackages()

		site_factory = interfaces.ISiteLibraryFactory(global_library)

		site_lib = site_factory.library_for_site_named( 'foobar' )

		assert_that( site_lib,
					 validly_provides( interfaces.IPersistentContentPackageLibrary ))

		site_path = os.path.join( global_library._enumeration.root.absolute_path,
								  'sites',
								  'foobar',)

		assert_that( site_lib._enumeration,
					 has_property('absolute_path', site_path ) )

		# should do nothing
		site_lib.syncContentPackages()

		# since they are not yet arranged in a site hierarchy, this one
		# doesn't have access to its parent contents yet.
		assert_that( site_lib, has_property( 'contentPackages', is_empty() ))

	def test_state(self):
		unit = filesystem.FilesystemContentUnit()
		unit._v_foo = 1
		assert_that( unit.__getstate__(), is_({} ))

		unit = filesystem.PersistentFilesystemContentUnit()
		unit._v_foo = 1
		unit._foo = 42
		assert_that( unit.__getstate__(), is_( {'_foo': 42} ))

class TestGlobalFilesystemLibrary(ContentlibraryLayerTest):

	def setUp(self):
		global_library = self.global_library = filesystem.GlobalFilesystemContentPackageLibrary( os.path.dirname(__file__) )
		global_library.syncContentPackages()

		component.getGlobalSiteManager().registerUtility( global_library,
														  provided=interfaces.IContentPackageLibrary )

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.global_library,
															provided=interfaces.IContentPackageLibrary )

	def testGlobalPickle(self):

		new_lib = pickle.loads(pickle.dumps(self.global_library))

		assert_that( new_lib, is_(same_instance(self.global_library)) )

		enum = self.global_library._enumeration
		new_enum = pickle.loads(pickle.dumps(enum))

		assert_that( new_enum, is_( same_instance(enum)))

	def testPickleOfSiteLibWhenGlobalPathChanges(self):
		global_library = self.global_library
		site_factory = interfaces.ISiteLibraryFactory(global_library)

		site_lib = site_factory.library_for_site_named( 'localsite' )

		assert_that( site_lib,
					 validly_provides( interfaces.IPersistentContentPackageLibrary ))

		site_path = os.path.join( global_library._enumeration.root.absolute_path,
								  'sites',
								  'localsite',)

		assert_that( site_lib._enumeration,
					 has_property('absolute_path', site_path ) )

		site_lib.syncContentPackages()

		content_package = site_lib[0]
		assert_that( content_package, has_property('absolute_path',
												   os.path.join(site_path, 'TestFilesystem', 'index.html')) )

		sites = pickle.dumps(site_lib)

		# Now if we change the global library path, this
		# should all change too
		global_library._enumeration.root.absolute_path = '/DNE/Hah'

		new_site_lib = pickle.loads(sites)
		new_enum = new_site_lib._enumeration

		getattr(new_enum, 'absolute_path')

		assert_that( new_enum, has_property('absolute_path', '/DNE/Hah/sites/localsite'))

		new_content_package = new_site_lib[0]
		assert_that( new_content_package, has_property('absolute_path', '/DNE/Hah/sites/localsite/TestFilesystem/index.html'))
