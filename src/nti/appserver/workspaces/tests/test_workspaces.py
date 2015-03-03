#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import all_of
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_value

from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import greater_than_or_equal_to
does_not = is_not

from zope import component
from zope import interface

from zope.location import location
from zope.location import interfaces as loc_interfaces

from zope.schema import interfaces as sch_interfaces

from zc import intid as zc_intid

from persistent import Persistent

import transaction

from nti.ntiids import ntiids
from nti.dataserver import  users
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import toExternalObject

from .. import FriendsListContainerCollection
from .. import UserEnumerationWorkspace as UEW
from .. import ContainerEnumerationWorkspace as CEW
from .. import HomogeneousTypedContainerCollection as HTCW
from .. import UserService, _UserPagesCollection as UserPagesCollection

from ..interfaces import IWorkspace
from ..interfaces import ICollection

from nti.appserver import tests

from nti.dataserver.tests import mock_dataserver

# Must create the application so that the views
# are registered, since we depend on those
# registrations to generate links.
# TODO: Break this dep.
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestContainerEnumerationWorkspace(ApplicationLayerTest):

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
		interface.alsoProvides( container, ICollection )
		assert_that( ICollection( container ), is_(container) )
		assert_that( list( cew.collections ), is_([container]) )

		# adaptable to a collection
		container = C()
		icontainer.conts = (container,)
		
		class Adapter(object):
			interface.implements(ICollection)
			component.adapts(ITestI)
			def __init__(self, obj ):
				self.obj = obj

		assert_that(ICollection( container, None ), is_(none()) )
		component.provideAdapter( Adapter )

		# We discovered that pyramid setup hooking ZCA fails to set the
		# local site manager as a child of the global site manager. if this
		# doesn't happen then the following test fails. We cause this connection
		# to be true in our test base, but that means that we don't really
		# test both branches of the or condition.
		assert_that( ICollection( container, None ), is_(Adapter) )
		assert_that( component.getAdapter( container, ICollection ), is_(Adapter) )

		assert_that( list( cew.collections )[0], is_( Adapter ) )

class MockRoot(object):
	interface.implements(loc_interfaces.IRoot)
	__parent__ = None
	__name__ = None

class TestUserEnumerationWorkspace(ApplicationLayerTest):

	@mock_dataserver.WithMockDSTrans
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
		uew.__parent__.__name__ = ''

		# Expecting the pages collection at least
		assert_that( uew.collections, has_length( greater_than_or_equal_to( 1 ) ) )
		
		# which in turn has one container
		assert_that( uew.pages_collection.container, has_length( 1 ) )
		root = uew.pages_collection.container[0]
		ext_obj = toExternalObject( root )
		
		__traceback_info__ = ext_obj
		
		assert_that( ext_obj, has_entry( 'ID', ntiids.ROOT ) )
		self.require_link_href_with_rel( ext_obj, 'RecursiveStream' )

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
		ext_obj = toExternalObject( root, request=self.beginRequest() )
		__traceback_info__ = ext_obj
		assert_that( ext_obj, has_entry( 'ID', ntiids.ROOT ) )
		assert_that( ext_obj, has_entry( 'Class', 'PageInfo' ) )
		assert_that( ext_obj, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		self.require_link_href_with_rel( ext_obj, 'RecursiveStream' )

		[shared] = [c for c in uew.pages_collection.container if c.ntiid == PersistentContained.containerId]

		ext_obj = toExternalObject( shared, request=self.beginRequest() )
		assert_that( ext_obj, has_entry( 'ID', PersistentContained.containerId ) )
		for rel in ('UserGeneratedData', 'RecursiveUserGeneratedData',
					'Stream', 'RecursiveStream',
					'UserGeneratedDataAndRecursiveStream',
					'RelevantUserGeneratedData',
					'Glossary',
					'TopUserSummaryData', 'UniqueMinMaxSummary'):
			self.require_link_href_with_rel( ext_obj, rel )

		transaction.doom()

class TestHomogeneousTypedContainerCollection(ApplicationLayerTest):

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

class TestUserService(ApplicationLayerTest):

	@mock_dataserver.WithMockDSTrans
	def test_external_coppa_capabilities(self):
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )
		service = UserService( user )

		ext_object = toExternalObject( service )

		assert_that(ext_object, has_entry('CapabilityList', has_length(2)))
		assert_that(ext_object, has_entry('CapabilityList', has_item(u'nti.platform.forums.communityforums')))
		assert_that(ext_object, has_entry('CapabilityList', has_item(u'nti.platform.customization.can_change_password')))

	@mock_dataserver.WithMockDSTrans
	def test_external(self):
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		service = UserService( user )

		ext_object = toExternalObject( service )
		__traceback_info__ = ext_object
		# The user should have some capabilities
		assert_that( ext_object, has_entry( 'CapabilityList', has_item( u'nti.platform.p2p.chat' ) ) )
		assert_that( ext_object, has_entry( 'CapabilityList', has_item( u'nti.platform.p2p.sharing' ) ) )
		# The global workspace should have a Link
		assert_that( ext_object['Items'], has_item(has_entry( 'Title', 'Global' )) )
		# Can't check links here, that comes from application configuration.
		# See test_usersearch.
		# And the User resource should have a Pages collection that also has
		# a link--this one pre-rendered
		user_wss = [x for x in ext_object['Items'] if x['Title'] == user.username]
		assert_that( user_wss, has_length( 1 ))
		user_ws, = user_wss
		assert_that( user_ws, has_entry( 'Title', user.username ) )
		assert_that( user_ws, has_entry( 'Items', has_item( all_of( has_entry( 'Title', 'Pages' ),
																	has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Pages' ) ) ) ) )
		assert_that( user_ws, has_entry( 'Items', has_item( has_entry( 'Links', has_item( has_entry('Class', 'Link')) ) ) ) )
		assert_that( user_ws['Items'], has_item( has_entry( 'Links', has_item(
			has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Search/RecursiveUserGeneratedData' ) ) ) ) )

		assert_that( user_ws['Items'], has_item( has_entry( 'Title', 'Boards' ) ) )

	@mock_dataserver.WithMockDSTrans
	def test_user_pages_collection_accepts_only_external_types(self):
		#"A user's Pages collection only claims to accept things that are externally creatable."
		# We prove this via a negative, so unfortunately this is not such
		# a great test
		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		ws = UEW(user)
		assert_that( 'application/vnd.nextthought.transcriptsummary', is_not( is_in( list(UserPagesCollection(ws).accepts) ) ) )
		assert_that( 'application/vnd.nextthought.canvasurlshape', is_in( list(UserPagesCollection(ws).accepts) ) )
		assert_that( 'application/vnd.nextthought.bookmark', is_in( list(UserPagesCollection(ws).accepts) ) )

	@mock_dataserver.WithMockDSTrans
	def test_user_pages_collection_restricted(self):
		#"A set of restrictions apply by default to what can be created"

		user = users.User.create_user( dataserver=self.ds, username='sjohnson@nextthought.com' )
		ws = UEW(user)
		assert_that( 'application/vnd.nextthought.canvasurlshape', is_in( list(UserPagesCollection(ws).accepts) ) )
		uew_ext = toExternalObject( ws )
		# And the blog, even though it's never been used
		assert_that( uew_ext['Items'], has_item( has_entry( 'Title', 'Blog' ) ) )


		# Making it ICoppaUser cuts that out
		interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )
		assert_that( 'application/vnd.nextthought.canvasurlshape', is_not( is_in( list(UserPagesCollection(ws).accepts) ) ) )

		# and from the vocab
		vocab = component.getUtility( sch_interfaces.IVocabularyFactory, "Creatable External Object Types" )( user )
		terms = [x.token for x in vocab]
		assert_that( 'application/vnd.nextthought.canvasurlshape', is_not( is_in( terms ) ) )


import os
import shutil
import tempfile

import pyramid.interfaces

from nti.appserver import pyramid_authorization

from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as DynamicLibrary

from nti.app.testing.layers import NewRequestLayerTest

class TestLibraryCollectionDetailExternalizer(NewRequestLayerTest):

	def setUp(self):
		super(TestLibraryCollectionDetailExternalizer,self).setUp()

		self.__policy = component.queryUtility( pyramid.interfaces.IAuthenticationPolicy )
		self.__acl_policy = component.queryUtility( pyramid.interfaces.IAuthorizationPolicy )

		self.temp_dir = tempfile.mkdtemp()
		self.entry_dir =  os.path.join( self.temp_dir, 'TheEntry' )
		os.mkdir( self.entry_dir )
		with open( os.path.join( self.entry_dir, 'eclipse-toc.xml' ), 'w' ) as f:
			f.write( """<?xml version="1.0"?>
			<toc NTIRelativeScrollHeight="58" href="index.html"
			icon="icons/Faa%20Aviation%20Maintenance%20Technician%20Knowledge%20Test%20Guide-Icon.png"
			label="FAA Aviation Maintenance Technician Knowledge Test" ntiid="tag:nextthought.com,2011-10:foo-bar-baz" thumbnail="./thumbnails/index.png">
			<topic label="C1" href="faa-index.html" ntiid="tag:nextthought.com,2011-10:foo-bar-baz.child"/>
			</toc>""")
		self.library = DynamicLibrary( self.temp_dir )
		self.library.syncContentPackages()

		class Policy(object):
			interface.implements( pyramid.interfaces.IAuthenticationPolicy )
			def authenticated_userid( self, request ):
				return 'jason.madden@nextthought.com'
			def effective_principals( self, request ):
				return [nti_interfaces.IPrincipal(x) for x in [	self.authenticated_userid(request), 
																nti_interfaces.AUTHENTICATED_GROUP_NAME,
																nti_interfaces.EVERYONE_GROUP_NAME]]

		self.policy = Policy()
		component.provideUtility( self.policy )
		self.acl_policy = pyramid_authorization.ZopeACLAuthorizationPolicy()
		component.provideUtility( self.acl_policy )

		self.library_workspace = component.getMultiAdapter( (self.library, self.request), IWorkspace )
		self.library_collection = self.library_workspace.collections[0]

	def tearDown(self):
		shutil.rmtree( self.temp_dir )
		component.getGlobalSiteManager().unregisterUtility( self.policy )
		component.getGlobalSiteManager().unregisterUtility( self.acl_policy )
		if self.__policy:
			component.provideUtility(self.__policy)
		if self.__acl_policy:
			component.provideUtility(self.__acl_policy)

		super(TestLibraryCollectionDetailExternalizer,self).tearDown()

	def test_no_acl_file(self):
		external = ext_interfaces.IExternalObject( self.library_collection ).toExternalObject()
		assert_that( external, has_entry( 'titles', has_length( 1 ) ) )

	def test_malformed_acl_file_denies_all(self):
		with open( os.path.join( self.entry_dir, '.nti_acl' ), 'w' ) as f:
			f.write( "This file is invalid" )
		external = ext_interfaces.IExternalObject( self.library_collection ).toExternalObject()
		assert_that( external, has_entry( 'titles', has_length( 0 ) ) )

	def test_specific_acl_file_forbids(self):
		acl_file = os.path.join( self.entry_dir, '.nti_acl' )
		with open( acl_file, 'w' ) as f:
			f.write( "Allow:User:[nti.actions.create]\n" )
			f.write( 'Deny:system.Everyone:All\n' )

		external = toExternalObject( self.library_collection )
		assert_that( external, has_entry( 'titles', has_length( 0 ) ) )

	def test_specific_acl_to_user(self):
		acl_file = os.path.join( self.entry_dir, '.nti_acl' )

		# Now, grant it to a user
		with open( acl_file, 'w' ) as f:
			f.write( "Allow:jason.madden@nextthought.com:[zope.View]\n" )

		external = toExternalObject( self.library_collection )
		assert_that( external, has_entry( 'titles', has_length( 1 ) ) )

	def test_specific_acl_to_user_chapter(self):
		acl_file = os.path.join( self.entry_dir, '.nti_acl' )

		# Back to the original entry on the ACL, denying it to everyone
		with open( acl_file, 'w' ) as f:
			f.write( "Allow:User:[nti.actions.create]\n" )
			f.write( 'Deny:system.Everyone:All\n' )

		# But the first chapter is allowed to the user:
		with open( acl_file + '.1', 'w' ) as f:
			f.write( "Allow:jason.madden@nextthought.com:[zope.View]\n" )

		external = toExternalObject( self.library_collection )
		assert_that( external, has_entry( 'titles', has_length( 1 ) ) )

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver.users.tests.test_friends_lists import _dfl_sharing_fixture

class TestFriendsListContainerCollection(DataserverLayerTest, tests.TestBaseMixin):

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
