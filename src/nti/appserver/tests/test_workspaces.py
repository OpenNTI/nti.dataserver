#!/usr/bin/env python2.7
# unittests have too many methods for pylint. pylint can suck it.
#pylint: disable=R0904

from hamcrest import (assert_that, is_, none,
					  has_entry, has_length, has_item,
					  greater_than_or_equal_to, is_not,
					  all_of, is_in)

from nti.appserver.workspaces import ContainerEnumerationWorkspace as CEW
from nti.appserver.workspaces import UserEnumerationWorkspace as UEW
from nti.appserver.workspaces import HomogeneousTypedContainerCollection as HTCW
from nti.appserver.workspaces import UserService, _UserEnrolledClassSectionsCollection as _UserClassesCollection, _UserPagesCollection as UserPagesCollection


from nti.appserver import tests
from nti.appserver import interfaces as app_interfaces

from nti.ntiids import ntiids
from nti.dataserver import links, users, providers
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import toExternalObject, to_external_object
from nti.externalization import oids as ext_oids
from nti.dataserver.tests import mock_dataserver

from zope import interface
from zope.location import location
from zope.location import interfaces as loc_interfaces
from zope import component
from persistent import Persistent
import urllib

class TestContainerEnumerationWorkspace(tests.ConfiguringTestBase):


	def test_parent(self):
		loc = location.Location()
		loc.__parent__ = self
		assert_that( CEW(loc).__parent__, is_(self) )
		loc.__parent__ = None
		assert_that( CEW(loc).__parent__, is_( none() ) )


	def test_name( self ):
		loc = location.Location()
		assert_that( CEW( loc ).name, is_(none()))
		loc.__name__ = 'Name'
		assert_that( CEW( loc ).name, is_(loc.__name__))
		assert_that( CEW( loc ).__name__, is_(loc.__name__))
		del loc.__name__
		loc.container_name = 'Name'
		assert_that( CEW( loc ).name, is_( loc.container_name) )

		cew = CEW(loc)
		cew.__name__ = 'NewName'
		assert_that( cew.name, is_( 'NewName' ) )
		assert_that( cew.__name__, is_( 'NewName' ) )


	def test_collections(self):
		class Iter(object):
			conts = ()
			def itercontainers(self):
				return iter(self.conts)

		class ITestI(interface.Interface): pass

		class C(object):
			interface.implements(ITestI)

		container = C()
		icontainer = Iter()
		icontainer.conts = (container,)

		# not a collection
		cew = CEW( icontainer )
		assert_that( list( cew.collections ), is_([]) )
		# itself a collection
		interface.alsoProvides( container, app_interfaces.ICollection )
		assert_that( app_interfaces.ICollection( container ), is_(container) )
		assert_that( list( cew.collections ), is_([container]) )

		# adaptable to a collection
		container = C()
		icontainer.conts = (container,)
		class Adapter(object):
			interface.implements(app_interfaces.ICollection)
			component.adapts(ITestI)
			def __init__(self, obj ):
				self.obj = obj

		assert_that( app_interfaces.ICollection( container, None ), is_(none()) )
		component.provideAdapter( Adapter )

		# We discovered that pyramid setup hooking ZCA fails to set the
		# local site manager as a child of the global site manager. if this
		# doesn't happen then the following test fails. We cause this connection
		# to be true in our test base, but that means that we don't really
		# test both branches of the or condition.
		assert_that( app_interfaces.ICollection( container, None ), is_(Adapter) )
		assert_that( component.getAdapter( container, app_interfaces.ICollection ), is_(Adapter) )

		assert_that( list( cew.collections )[0], is_( Adapter ) )

class MockRoot(object):
	interface.implements(loc_interfaces.IRoot)
	__parent__ = None
	__name__ = None

class TestUserEnumerationWorkspace(tests.ConfiguringTestBase):

	def test_root_ntiid(self):
		class MockUser(object):
			interface.implements(nti_interfaces.IUser)
			__name__ = 'user@place'
			username = 'user@place'
			def itercontainers(self):
				return iter( () )
			def iterntiids(self):
				return iter( () )
		uew = UEW( MockUser() )

		uew.__parent__ = MockRoot()

		# Expecting the pages collection at least
		assert_that( uew.collections, has_length( greater_than_or_equal_to( 1 ) ) )
		# which in turn has one container
		assert_that( uew.collections[0].container, has_length( 1 ) )
		root = uew.collections[0].container[0]
		ext_obj = to_external_object( root )
		assert_that( ext_obj, has_entry( 'ID', ntiids.ROOT ) )
		assert_that( ext_obj, has_entry( 'Links', has_length( 1 ) ) )
		assert_that( ext_obj['Links'][0], has_entry( 'rel', 'RecursiveStream' ) )

	@mock_dataserver.WithMockDSTrans
	def test_shared_container(self):
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		class PersistentContained(Persistent):
			interface.implements(nti_interfaces.IContained,nti_interfaces.IZContained)
			__name__ = '1'
			id = __name__
			__parent__ = None
			containerId = 'tag:nextthought.com,2011-10:test.user.1@nextthought.com-OID-0x0bd6:5573657273'

		user._addSharedObject( PersistentContained() )
		uew = UEW( user )

		# Expecting pages collection, devices, friends lists
		assert_that( uew.collections, has_length( greater_than_or_equal_to( 3 ) ) )
		# which in turn has two containers, the root and the shared
		assert_that( uew.collections[2].container, has_length( 2 ) )
		root = uew.collections[2].container[0]
		ext_obj = to_external_object( root )
		assert_that( ext_obj, has_entry( 'ID', ntiids.ROOT ) )
		assert_that( ext_obj, has_entry( 'Class', 'PageInfo' ) )
		assert_that( ext_obj, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( ext_obj, has_entry( 'Links', has_length( 1 ) ) )
		assert_that( ext_obj['Links'][0], has_entry( 'rel', 'RecursiveStream' ) )


		shared = uew.collections[2].container[1]
		ext_obj = to_external_object( shared )
		assert_that( ext_obj, has_entry( 'ID', PersistentContained.containerId ) )
		#['UserGeneratedData', 'RecursiveUserGeneratedData', 'Stream', 'RecursiveStream', 'UserGeneratedDataAndRecursiveStream']
		assert_that( ext_obj, has_entry( 'Links', has_length( 5 ) ) )




class TestHomogeneousTypedContainerCollection (tests.ConfiguringTestBase):


	def test_parent(self):
		loc = location.Location()
		loc.__parent__ = self
		assert_that( HTCW(loc).__parent__, is_(self) )
		loc.__parent__ = None
		assert_that( HTCW(loc).__parent__, is_( none() ) )


	def test_name( self ):
		loc = location.Location()
		assert_that( HTCW( loc ).name, is_(none()))
		loc.__name__ = 'Name'
		assert_that( HTCW( loc ).name, is_(loc.__name__))
		assert_that( HTCW( loc ).__name__, is_(loc.__name__))
		del loc.__name__
		loc.container_name = 'Name'
		assert_that( HTCW( loc ).name, is_( loc.container_name) )

		cew = HTCW(loc)
		cew.__name__ = 'NewName'
		assert_that( cew.name, is_( 'NewName' ) )
		assert_that( cew.__name__, is_( 'NewName' ) )

from nti.dataserver.classes import ClassInfo, SectionInfo

class TestUserService(tests.ConfiguringTestBase):

	@mock_dataserver.WithMockDSTrans
	def test_external(self):
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		service = UserService( user )

		ext_object = toExternalObject( service )
		# The global workspace should have a Link
		assert_that( ext_object['Items'][1], has_entry( 'Title', 'Global' ) )
		assert_that( ext_object['Items'][1], has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/UserSearch' ) ) ) )

		# And the User resource should have a Pages collection that also has
		# a link--this one pre-rendered
		user_ws = ext_object['Items'][0]
		assert_that( user_ws, has_entry( 'Title', user.username ) )
		assert_that( user_ws, has_entry( 'Items', has_item( all_of( has_entry( 'Title', 'Pages' ),
																	has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Pages' ) ) ) ) )
		assert_that( user_ws, has_entry( 'Items', has_item( has_entry( 'Links', has_item( has_entry('Class', 'Link')) ) ) ) )
		assert_that( user_ws['Items'][2]['Links'][0],
					 has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Search/RecursiveUserGeneratedData' ) )

		# And a class
		assert_that( user_ws, has_entry( 'Items', has_item( all_of( has_entry( 'Title', 'EnrolledClassSections' ),
																	has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/EnrolledClassSections' ) ) ) ) )

		# A provider should show in the providers workspace
		providers.Provider.create_provider( self.ds, username='OU' )
		ext_object = toExternalObject( service )
		assert_that( ext_object['Items'], has_item( all_of( has_entry( 'Title', 'providers' ),
															has_entry( 'Items', has_item( has_entry( 'href', '/dataserver2/providers/OU' ) ) ),
															# Because there is no authentication policy in use, we should be able to write to it
															has_entry( 'Items', has_item( has_entry( 'accepts', has_item( 'application/vnd.nextthought.classinfo' ) ) ) ) ) ) )

class TestUserClassesCollection(tests.ConfiguringTestBase):

	@mock_dataserver.WithMockDSTrans
	def test_external( self ):
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		ou = providers.Provider.create_provider( self.ds, username='OU' )

		clazz = ClassInfo( ID='CS5201' )
		clazz.containerId = 'Classes'
		ou.addContainedObject( clazz )
		section = SectionInfo( ID='CS5201.501' )
		clazz.add_section( section )
		section.enroll( 'sjohnson@nextthought.com' )

		assert_that( clazz.__parent__, is_not( none() ) )

		ext_object = toExternalObject( _UserClassesCollection( user ) )
		assert_that( ext_object, has_entry( 'Title', 'EnrolledClassSections' ) )
		assert_that( ext_object, has_entry( 'Items',
											has_item( has_entry( 'href',
																 '/dataserver2/Objects/' + urllib.quote( ext_oids.to_external_ntiid_oid( section ) ) ) ) ) )
																# '/dataserver2/providers/OU/Classes/CS5201/CS5201.501' ) ) ) )

def test_user_pages_collection_accepts_only_external_types():
	"A user's Pages collection only claims to accept things that are externally creatable."
	# We prove this via a negative, so unfortunately this is not such
	# a great test

	assert_that( 'application/vnd.nextthought.transcriptsummary', is_not( is_in( list(UserPagesCollection(None).accepts) ) ) )

import tempfile
import shutil
import os

from nti.contentlibrary.filesystem import DynamicLibrary

import pyramid.interfaces
from pyramid.threadlocal import get_current_request

class TestLibraryCollectionDetailExternalizer(tests.ConfiguringTestBase):

	def setUp(self):
		super(TestLibraryCollectionDetailExternalizer,self).setUp()
		self.temp_dir = tempfile.mkdtemp()
		self.entry_dir =  os.path.join( self.temp_dir, 'TheEntry' )
		os.mkdir( self.entry_dir )
		with open( os.path.join( self.entry_dir, 'eclipse-toc.xml' ), 'w' ) as f:
			f.write( """<?xml version="1.0"?>
			<toc NTIRelativeScrollHeight="58" href="index.html"
			icon="icons/Faa%20Aviation%20Maintenance%20Technician%20Knowledge%20Test%20Guide-Icon.png"
			label="FAA Aviation Maintenance Technician Knowledge Test" ntiid="faa-mathcounts-1" thumbnail="./thumbnails/index.png">
			<topic label="C1" href="faa-index.html"/>
			</toc>""")
		self.library = DynamicLibrary( self.temp_dir )
		self.library_workspace = component.getAdapter( self.library, app_interfaces.IWorkspace )
		self.library_collection = self.library_workspace.collections[0]

		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'
			def effective_principals( self, request ):
				return [nti_interfaces.IPrincipal(x) for x in [self.authenticated_userid(request), nti_interfaces.AUTHENTICATED_GROUP_NAME]]
		get_current_request().registry.registerUtility( Policy() )
		get_current_request().registry.registerUtility( pyramid.authorization.ACLAuthorizationPolicy() )

	def tearDown(self):
		shutil.rmtree( self.temp_dir )
		super(TestLibraryCollectionDetailExternalizer,self).tearDown()

	def test_no_acl_file(self):
		external = ext_interfaces.IExternalObject( self.library_collection ).toExternalObject()
		assert_that( external, has_entry( 'titles', has_length( 1 ) ) )

	def test_malformed_acl_file_denies_all(self):
		with open( os.path.join( self.entry_dir, '.nti_acl' ), 'w' ) as f:
			f.write( "This file is invalid" )
		external = ext_interfaces.IExternalObject( self.library_collection ).toExternalObject()
		assert_that( external, has_entry( 'titles', has_length( 0 ) ) )


	def test_specific_acl_file(self):
		with open( os.path.join( self.entry_dir, '.nti_acl' ), 'w' ) as f:
			f.write( "Allow:User:[nti.actions.create]" )

		external = ext_interfaces.IExternalObject( self.library_collection ).toExternalObject()
		assert_that( external, has_entry( 'titles', has_length( 0 ) ) )

		with open( os.path.join( self.entry_dir, '.nti_acl' ), 'w' ) as f:
			f.write( "Allow:jason.madden@nextthought.com:[zope.View]" )

		external = ext_interfaces.IExternalObject( self.library_collection ).toExternalObject()
		assert_that( external, has_entry( 'titles', has_length( 1 ) ) )
