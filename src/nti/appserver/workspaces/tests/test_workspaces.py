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
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_inanyorder
from hamcrest import greater_than_or_equal_to
does_not = is_not

import transaction

from persistent import Persistent

from zope import component
from zope import interface

from zope.authentication.interfaces import IPrincipal

from zope.location import location
from zope.location import interfaces as loc_interfaces

from zope.schema import interfaces as sch_interfaces

from zc import intid as zc_intid

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.appserver.workspaces import Service
from nti.appserver.workspaces import UserService
from nti.appserver.workspaces import FriendsListContainerCollection
from nti.appserver.workspaces import UserEnumerationWorkspace as UEW
from nti.appserver.workspaces import ContainerEnumerationWorkspace as CEW
from nti.appserver.workspaces import HomogeneousTypedContainerCollection as HTCW
from nti.appserver.workspaces import _UserPagesCollection as UserPagesCollection

from nti.appserver.workspaces.interfaces import ICollection

from nti.dataserver import  users
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.externalization import toExternalObject

from nti.ntiids import ntiids

from nti.appserver import tests

from nti.dataserver.tests import mock_dataserver

# Must create the application so that the views
# are registered, since we depend on those
# registrations to generate links.
# TODO: Break this dep.
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver.users.tests.test_friends_lists import _dfl_sharing_fixture

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
			def iter_containers(self):
				return iter(self.conts)
			itercontainers = iter_containers

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
			def iter_containers(self):
				return iter( () )
			itercontainers = iter_containers

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
					'Glossary'):
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

class TestService(ApplicationLayerTest):

	@mock_dataserver.WithMockDSTrans
	def test_non_user_workspaces(self):
		principal = IPrincipal('system.Unknown')
		service = Service(principal)

		ext_object = toExternalObject(service)

		#We should have a global workspace
		assert_that(ext_object['Items'], has_item(has_entry( 'Title', 'Global' )))

		#We shouldn't have user specific workspaces
		user_wss = [x for x in ext_object['Items'] if not x['Title'] or x['Title'] == 'system.Unknown' ]
		assert_that( user_wss, has_length( 0 ))

class TestUserService(ApplicationLayerTest):

	@mock_dataserver.WithMockDSTrans
	def test_external_coppa_capabilities(self):
		user = users.User.create_user( dataserver=self.ds, username='coppa_user' )
		interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )
		service = UserService( user )

		ext_object = toExternalObject( service )

		assert_that(ext_object, has_entry('CapabilityList', has_length(3)))
		assert_that(ext_object, has_entry('CapabilityList',
											contains_inanyorder(
													u'nti.platform.forums.dflforums',
													u'nti.platform.forums.communityforums',
													u'nti.platform.customization.can_change_password')))

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
																	has_entry( 'href', '/dataserver2/users/sjohnson@nextthought.com/Pages' ) ) ) ) )
		for membership_name in ('FriendsLists', 'Groups', 'Communities', 'DynamicMemberships'):
			assert_that( user_ws, has_entry( 'Items', has_item( all_of( has_entry( 'Title', membership_name ),
																		has_entry( 'href', '/dataserver2/users/sjohnson@nextthought.com/' + membership_name ) ) ) ) )
		assert_that( user_ws, has_entry( 'Items', has_item( has_entry( 'Links', has_item( has_entry('Class', 'Link')) ) ) ) )
		assert_that( user_ws['Items'], has_item( has_entry( 'Links', has_item(
			has_entry( 'href', '/dataserver2/users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData' ) ) ) ) )

		assert_that( user_ws['Items'], has_item( has_entry( 'Title', 'Boards' ) ) )

		# And, if we have a site community, it's exposed.
		site_policy = component.queryUtility( ISitePolicyUserEventListener )
		site_policy.COM_USERNAME = 'community_username'
		ext_object = toExternalObject( service )
		assert_that( ext_object, has_entry( 'SiteCommunity', 'community_username' ) )

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

class TestFriendsListContainerCollection(DataserverLayerTest, tests.TestBaseMixin):

	@mock_dataserver.WithMockDSTrans
	def test_container_only_friends_list(self):
		owner_user, member_user, _member_user2, parent_dfl = _dfl_sharing_fixture( self.ds )

		owner_fl_cont = FriendsListContainerCollection( owner_user.friendsLists )
		assert_that( owner_fl_cont, has_property( 'container', has_length( 0 ) ) )

		# The member container adds the DFL
		member_cont = FriendsListContainerCollection( member_user.friendsLists )
		assert_that( member_cont, has_property( 'container', has_length( 0 ) ) )

		assert_that( member_cont.container, has_property( '__name__', owner_fl_cont.__name__ ) )
		assert_that( member_cont.container, has_property( '__parent__', member_user ) )

		# Now, if we cheat and remove the member from the DFL, but leave the relationship
		# in place, then we handle that
		parent_dfl.removeFriend( member_user )
		member_user.record_dynamic_membership( parent_dfl )
		assert_that( list(parent_dfl), does_not( has_item( member_user ) ) )
		assert_that( list(member_user.dynamic_memberships), has_item( parent_dfl ) )

		assert_that( member_cont, has_property( 'container', has_length( 0 ) ) )

		# The same magic happens for _get_dynamic_sharing_targets_for_read
		# assert_that( member_user._get_dynamic_sharing_targets_for_read(), does_not( has_item( parent_dfl ) ) )
