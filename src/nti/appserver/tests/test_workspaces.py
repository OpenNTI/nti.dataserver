#!/usr/bin/env python
# unittests have too many methods for pylint. pylint can suck it.
#pylint: disable=R0904

from hamcrest import (assert_that, is_, none,
					  has_entry, has_length, has_item,
					  greater_than_or_equal_to, is_not,
					  all_of, is_in)
from hamcrest import has_property
from hamcrest import has_value
from hamcrest import has_entries
does_not = is_not
import unittest

from nti.appserver.workspaces import ContainerEnumerationWorkspace as CEW
from nti.appserver.workspaces import UserEnumerationWorkspace as UEW
from nti.appserver.workspaces import HomogeneousTypedContainerCollection as HTCW
from nti.appserver.workspaces import UserService, _UserPagesCollection as UserPagesCollection
from nti.appserver.workspaces import FriendsListContainerCollection

from nti.appserver import tests
from nti.appserver import interfaces as app_interfaces

from nti.ntiids import ntiids
from nti.dataserver import  users
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import toExternalObject, to_external_object
from nti.dataserver.tests import mock_dataserver

from zope import interface
from zope.location import location
from zope.location import interfaces as loc_interfaces
from zope import component
from zope.schema import interfaces as sch_interfaces
from zc import intid as zc_intid
from persistent import Persistent
import transaction

import nti.testing.base

setUpModule = lambda: nti.testing.base.module_setup( set_up_packages=(nti.appserver,), features=('devmode','forums') )
tearDownModule = nti.testing.base.module_teardown

class TestContainerEnumerationWorkspace(unittest.TestCase):


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

class TestUserEnumerationWorkspace(unittest.TestCase,tests.TestBaseMixin):

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
		assert_that( uew.pages_collection.container, has_length( 1 ) )
		root = uew.pages_collection.container[0]
		ext_obj = to_external_object( root )
		__traceback_info__ = ext_obj
		assert_that( ext_obj, has_entry( 'ID', ntiids.ROOT ) )
		assert_that( ext_obj, has_entry( 'Links', has_length( greater_than_or_equal_to( 1 ) ) ) )
		assert_that( ext_obj['Links'][1], has_entry( 'rel', 'RecursiveStream' ) )

	@mock_dataserver.WithMockDSTrans
	def test_shared_container(self):
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		class PersistentContained(Persistent):
			interface.implements(nti_interfaces.IContained,nti_interfaces.IZContained)
			__name__ = '1'
			id = __name__
			__parent__ = None
			containerId = 'tag:nextthought.com,2011-10:test.user.1@nextthought.com-OID-0x0bd6:5573657273'

		pc = PersistentContained()
		component.getUtility( zc_intid.IIntIds ).register( pc )
		user._addSharedObject( pc )
		uew = UEW( user )

		# Expecting pages collection, devices, friends lists, blog, ...
		assert_that( uew.collections, has_length( greater_than_or_equal_to( 3 ) ) )
		# the pages collection  in turn has at least two containers, the root and the shared (plus the blog)
		assert_that( uew.pages_collection.container, has_length( greater_than_or_equal_to(  2 ) ) )
		# These come in sorted
		root = uew.pages_collection.container[0]
		ext_obj = to_external_object( root )
		__traceback_info__ = ext_obj
		assert_that( ext_obj, has_entry( 'ID', ntiids.ROOT ) )
		assert_that( ext_obj, has_entry( 'Class', 'PageInfo' ) )
		assert_that( ext_obj, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( ext_obj, has_entry( 'Links', has_length( greater_than_or_equal_to( 1 ) ) ) )
		assert_that( ext_obj['Links'][1], has_entry( 'rel', 'RecursiveStream' ) )


		[shared] = [c for c in uew.pages_collection.container if c.ntiid == PersistentContained.containerId]
		ext_obj = to_external_object( shared )
		assert_that( ext_obj, has_entry( 'ID', PersistentContained.containerId ) )
		#['UserGeneratedData', 'RecursiveUserGeneratedData', 'Stream', 'RecursiveStream', 'UserGeneratedDataAndRecursiveStream', 'Glossary']
		assert_that( ext_obj, has_entry( 'Links', has_length( greater_than_or_equal_to( 6 ) ) ) )

		transaction.doom()



class TestHomogeneousTypedContainerCollection (unittest.TestCase):


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

class TestUserService(unittest.TestCase,tests.TestBaseMixin):

	@mock_dataserver.WithMockDSTrans
	def test_external_coppa_capabilities(self):
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )
		service = UserService( user )

		ext_object = toExternalObject( service )
		# No defined capabilities
		assert_that(ext_object, has_entry('CapabilityList', has_length(1)))
		assert_that(ext_object, has_entry('CapabilityList', has_item(u'nti.platform.forums.communityforums')))


	@mock_dataserver.WithMockDSTrans
	def test_external(self):
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		service = UserService( user )

		ext_object = toExternalObject( service )
		# The user should have some capabilities
		assert_that( ext_object, has_entry( 'CapabilityList', has_item( u'nti.platform.p2p.chat' ) ) )
		assert_that( ext_object, has_entry( 'CapabilityList', has_item( u'nti.platform.p2p.sharing' ) ) )
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
		assert_that( user_ws['Items'], has_item( has_entry( 'Links', has_item(
			has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Search/RecursiveUserGeneratedData' ) ) ) ) )

	@mock_dataserver.WithMockDSTrans
	def test_user_pages_collection_accepts_only_external_types(self):
		"A user's Pages collection only claims to accept things that are externally creatable."
		# We prove this via a negative, so unfortunately this is not such
		# a great test
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		ws = UEW(user)
		assert_that( 'application/vnd.nextthought.transcriptsummary', is_not( is_in( list(UserPagesCollection(ws).accepts) ) ) )
		assert_that( 'application/vnd.nextthought.canvasurlshape', is_in( list(UserPagesCollection(ws).accepts) ) )
		assert_that( 'application/vnd.nextthought.bookmark', is_in( list(UserPagesCollection(ws).accepts) ) )

	@mock_dataserver.WithMockDSTrans
	def test_user_pages_collection_restricted(self):
		"A set of restrictions apply by default to what can be created"

		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		ws = UEW(user)
		assert_that( 'application/vnd.nextthought.canvasurlshape', is_in( list(UserPagesCollection(ws).accepts) ) )
		uew_ext = to_external_object( ws )
		# And the blog, even though it's never been used
		assert_that( uew_ext['Items'], has_item( has_entry( 'Title', 'Blog' ) ) )


		# Making it ICoppaUser cuts that out
		interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )
		assert_that( 'application/vnd.nextthought.canvasurlshape', is_not( is_in( list(UserPagesCollection(ws).accepts) ) ) )

		# and from the vocab
		vocab = component.getUtility( sch_interfaces.IVocabularyFactory, "Creatable External Object Types" )( user )
		terms = [x.token for x in vocab]
		assert_that( 'application/vnd.nextthought.canvasurlshape', is_not( is_in( terms ) ) )


import tempfile
import shutil
import os

from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as DynamicLibrary

import pyramid.interfaces

from pyramid.testing import setUp as psetUp
from pyramid.testing import DummyRequest
from nti.appserver import pyramid_authorization


class TestLibraryCollectionDetailExternalizer(unittest.TestCase,tests.TestBaseMixin):

	@classmethod
	def setUpClass( cls, request_factory=DummyRequest, request_args=(), security_policy_factory=None, force_security_policy=True ):
		"""
		:return: The `Configurator`, which is also in ``self.config``.
		"""

		super(TestLibraryCollectionDetailExternalizer,cls).setUpClass()

		cls.config = psetUp(registry=component.getGlobalSiteManager(),request=cls.request,hook_zca=False)

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
				return [nti_interfaces.IPrincipal(x) for x in [self.authenticated_userid(request), nti_interfaces.AUTHENTICATED_GROUP_NAME, nti_interfaces.EVERYONE_GROUP_NAME]]
		### XXX Breaks test isolation
		self.beginRequest()
		self.request.registry = component.getGlobalSiteManager()
		self.policy = Policy()
		component.provideUtility( self.policy )
		self.acl_policy = pyramid_authorization.ACLAuthorizationPolicy()
		component.provideUtility( self.acl_policy )

	def tearDown(self):
		shutil.rmtree( self.temp_dir )
		component.getGlobalSiteManager().unregisterUtility( self.policy )
		component.getGlobalSiteManager().unregisterUtility( self.acl_policy )
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
		acl_file = os.path.join( self.entry_dir, '.nti_acl' )
		with open( acl_file, 'w' ) as f:
			f.write( "Allow:User:[nti.actions.create]\n" )
			f.write( 'Deny:system.Everyone:All\n' )

		external = to_external_object( self.library_collection )
		assert_that( external, has_entry( 'titles', has_length( 0 ) ) )

		# Now, grant it to a user
		with open( acl_file, 'w' ) as f:
			f.write( "Allow:jason.madden@nextthought.com:[zope.View]\n" )

		# clear caches
		import nti.contentlibrary.contentunit
		nti.contentlibrary.contentunit._clear_caches()
		self.beginRequest()

		external = to_external_object( self.library_collection )
		assert_that( external, has_entry( 'titles', has_length( 1 ) ) )


		# Back to the original entry on the ACL, denying it to everyone
		with open( acl_file, 'w' ) as f:
			f.write( "Allow:User:[nti.actions.create]\n" )
			f.write( 'Deny:system.Everyone:All\n' )

		# But the first chapter is allowed to the user:
		with open( acl_file + '.1', 'w' ) as f:
			f.write( "Allow:jason.madden@nextthought.com:[zope.View]\n" )

		# after clearing caches
		import nti.contentlibrary.contentunit
		nti.contentlibrary.contentunit._clear_caches()
		self.beginRequest()

		# it is still visible
		external = to_external_object( self.library_collection )
		assert_that( external, has_entry( 'titles', has_length( 1 ) ) )


from nti.dataserver.users.tests.test_friends_lists import _dfl_sharing_fixture

class TestFriendsListContainerCollection(unittest.TestCase,tests.TestBaseMixin):
	set_up_packages = ('nti.dataserver',)

	@mock_dataserver.WithMockDSTrans
	def test_container_with_dfl_memberships(self):
		owner_user, member_user, _member_user2, parent_dfl = _dfl_sharing_fixture( self.ds )

		owner_fl_cont = FriendsListContainerCollection( owner_user.friendsLists )

		assert_that( owner_fl_cont, has_property( 'container', is_( owner_user.friendsLists ) ) )
		assert_that( owner_fl_cont, has_property( 'container', has_property( '__name__', 'FriendsLists' ) ) )

		# The member container adds the DFL
		member_cont = FriendsListContainerCollection( member_user.friendsLists )
		assert_that( member_cont, has_property( 'container', is_not( member_user.friendsLists ) ) )
		assert_that( member_cont, has_property( 'container', has_value( parent_dfl ) ) )

		assert_that( member_cont.container, has_property( '__name__', owner_fl_cont.__name__ ) )
		assert_that( member_cont.container, has_property( '__parent__', member_user ) )

		# Now, if we cheat and remove the member from the DFL, but leave the relationship
		# in place, then we handle that
		parent_dfl.removeFriend( member_user )
		member_user.record_dynamic_membership( parent_dfl )
		assert_that( list(parent_dfl), does_not( has_item( member_user ) ) )
		assert_that( list(member_user.dynamic_memberships), has_item( parent_dfl ) )

		assert_that( member_cont, has_property( 'container', is_( member_user.friendsLists ) ) )

		# The same magic happens for _get_dynamic_sharing_targets_for_read
		assert_that( member_user._get_dynamic_sharing_targets_for_read(), does_not( has_item( parent_dfl ) ) )
