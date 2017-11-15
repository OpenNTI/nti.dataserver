#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import all_of
from hamcrest import not_none
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_inanyorder
from hamcrest import greater_than_or_equal_to
does_not = is_not

import transaction

from zope import component
from zope import interface

from zope.authentication.interfaces import IPrincipal

from zope.container.contained import Contained

from zope.intid.interfaces import IIntIds

from zope.location.interfaces import IRoot

from zope.location.location import Location

from zope.schema.interfaces import IVocabularyFactory

from persistent import Persistent

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.appserver.tests import TestBaseMixin

from nti.appserver.workspaces import Service
from nti.appserver.workspaces import UserService
from nti.appserver.workspaces import UserPagesCollection
from nti.appserver.workspaces import FriendsListContainerCollection
from nti.appserver.workspaces import UserEnumerationWorkspace as UEW
from nti.appserver.workspaces import ContainerEnumerationWorkspace as CEW
from nti.appserver.workspaces import HomogeneousTypedContainerCollection as HTCW

from nti.appserver.workspaces.interfaces import ICollection

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement
from nti.dataserver.interfaces import IContained as INTIContained

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver.users.tests.test_friends_lists import _dfl_sharing_fixture

from nti.dataserver.users.users import User

from nti.externalization.externalization import toExternalObject

from nti.ntiids import ntiids

# Must create the application so that the views
# are registered, since we depend on those
# registrations to generate links.
# TODO: Break this dep.
from nti.app.testing.application_webtest import ApplicationLayerTest


class TestContainerEnumerationWorkspace(ApplicationLayerTest):

    def test_parent(self):
        loc = Location()
        loc.__parent__ = self
        assert_that(CEW(loc).__parent__, is_(self))
        loc.__parent__ = None
        assert_that(CEW(loc).__parent__, is_(none()))

    def test_name(self):
        loc = Location()
        assert_that(CEW(loc).name, is_(none()))
        loc.__name__ = 'Name'
        assert_that(CEW(loc).name, is_(loc.__name__))
        assert_that(CEW(loc).__name__, is_(loc.__name__))
        del loc.__name__
        loc.container_name = 'Name'
        assert_that(CEW(loc).name, is_(loc.container_name))

        cew = CEW(loc)
        cew.__name__ = 'NewName'
        assert_that(cew.name, is_('NewName'))
        assert_that(cew.__name__, is_('NewName'))

    def test_collections(self):
        class Iter(object):
            conts = ()

            def iter_containers(self):
                return iter(self.conts)
            itercontainers = iter_containers

        class ITestI(interface.Interface):
            pass

        class C(object):
            interface.implements(ITestI)

        container = C()
        icontainer = Iter()
        icontainer.conts = (container,)

        # not a collection
        cew = CEW(icontainer)
        assert_that(list(cew.collections), is_([]))
        # itself a collection
        interface.alsoProvides(container, ICollection)
        assert_that(ICollection(container), is_(container))
        assert_that(list(cew.collections), is_([container]))

        # adaptable to a collection
        container = C()
        icontainer.conts = (container,)

        @component.adapter(ITestI)
        @interface.implementer(ICollection)
        class Adapter(object):

            def __init__(self, obj):
                self.obj = obj

        assert_that(ICollection(container, None), is_(none()))
        component.provideAdapter(Adapter)

        # We discovered that pyramid setup hooking ZCA fails to set the
        # local site manager as a child of the global site manager. if this
        # doesn't happen then the following test fails. We cause this connection
        # to be true in our test base, but that means that we don't really
        # test both branches of the or condition.
        assert_that(ICollection(container, None), is_(Adapter))
        assert_that(component.getAdapter(container, ICollection), is_(Adapter))

        assert_that(list(cew.collections)[0], is_(Adapter))


@interface.implementer(IRoot)
class MockRoot(Contained):
    pass


class TestUserEnumerationWorkspace(ApplicationLayerTest):

    @mock_dataserver.WithMockDSTrans
    def test_root_ntiid(self):

        @interface.implementer(IUser)
        class MockUser(object):
            __name__ = u'user@place'
            username = u'user@place'

            def iter_containers(self):
                return iter(())
            itercontainers = iter_containers

            def iterntiids(self):
                return iter(())
        uew = UEW(MockUser())

        uew.__parent__ = MockRoot()
        uew.__parent__.__name__ = ''

        # Expecting the pages collection at least
        assert_that(uew.collections, has_length(greater_than_or_equal_to(1)))

        # which in turn has one container
        assert_that(uew.pages_collection.container, has_length(1))
        root = uew.pages_collection.container[0]
        ext_obj = toExternalObject(root)

        __traceback_info__ = ext_obj

        assert_that(ext_obj, has_entry('ID', ntiids.ROOT))
        self.require_link_href_with_rel(ext_obj, 'RecursiveStream')

    @mock_dataserver.WithMockDSTrans
    def test_shared_container(self):
        user = User.create_user(dataserver=self.ds,
                                username='sjohnson@nextthought.com')

        @interface.implementer(INTIContained)
        class PersistentContained(Persistent):
            __name__ = u'1'
            __parent__ = None
            id = __name__
            containerId = u'tag:nextthought.com,2011-10:test.user.1@nextthought.com-OID-0x0bd6:5573657273'

        pc = PersistentContained()
        component.getUtility(IIntIds).register(pc)
        user._addSharedObject(pc)
        uew = UEW(user)

        # Expecting pages collection, devices, friends lists, blog, ...
        assert_that(uew.collections, has_length(greater_than_or_equal_to(3)))
        # the pages collection  in turn has at least two containers, the root
        # and the shared (plus the blog)
        assert_that(uew.pages_collection.container,
                    has_length(greater_than_or_equal_to(2)))
        # These come in sorted
        root = uew.pages_collection.container[0]
        ext_obj = toExternalObject(root, request=self.beginRequest())
        __traceback_info__ = ext_obj
        assert_that(ext_obj, has_entry('ID', ntiids.ROOT))
        assert_that(ext_obj,
                    has_entry('Class', 'PageInfo'))
        assert_that(ext_obj,
                    has_entry('MimeType', 'application/vnd.nextthought.pageinfo'))
        self.require_link_href_with_rel(ext_obj, 'RecursiveStream')

        [shared] = [
            c for c in uew.pages_collection.container
            if c.ntiid == PersistentContained.containerId
        ]

        ext_obj = toExternalObject(shared, request=self.beginRequest())
        assert_that(ext_obj, has_entry('ID', PersistentContained.containerId))
        for rel in ('UserGeneratedData', 'RecursiveUserGeneratedData',
                    'Stream', 'RecursiveStream',
                    'UserGeneratedDataAndRecursiveStream',
                    'RelevantUserGeneratedData',
                    'Glossary'):
            self.require_link_href_with_rel(ext_obj, rel)

        transaction.doom()


class TestHomogeneousTypedContainerCollection(ApplicationLayerTest):

    def test_parent(self):
        loc = Location()
        loc.__parent__ = self
        assert_that(HTCW(loc).__parent__, is_(self))
        loc.__parent__ = None
        assert_that(HTCW(loc).__parent__, is_(none()))

    def test_name(self):
        loc = Location()
        assert_that(HTCW(loc).name, is_(none()))
        loc.__name__ = 'Name'
        assert_that(HTCW(loc).name, is_(loc.__name__))
        assert_that(HTCW(loc).__name__, is_(loc.__name__))
        del loc.__name__
        loc.container_name = 'Name'
        assert_that(HTCW(loc).name, is_(loc.container_name))

        cew = HTCW(loc)
        cew.__name__ = 'NewName'
        assert_that(cew.name, is_('NewName'))
        assert_that(cew.__name__, is_('NewName'))


class TestService(ApplicationLayerTest):

    @mock_dataserver.WithMockDSTrans
    def test_non_user_workspaces(self):
        principal = IPrincipal(u'system.Unknown')
        service = Service(principal)

        ext_object = toExternalObject(service)

        # We should have a global workspace
        assert_that(ext_object['Items'],
                    has_item(has_entry('Title', 'Global')))

        # We shouldn't have user specific workspaces
        user_wss = [
            x for x in ext_object['Items']
            if not x['Title'] or x['Title'] == 'system.Unknown'
        ]
        assert_that(user_wss, has_length(0))


class TestUserService(ApplicationLayerTest):

    @mock_dataserver.WithMockDSTrans
    def test_external_coppa_capabilities(self):
        user = User.create_user(dataserver=self.ds,
                                username=u'coppa_user')
        interface.alsoProvides(user, ICoppaUserWithoutAgreement)
        service = UserService(user)

        ext_object = toExternalObject(service)

        assert_that(ext_object, has_entry('CapabilityList', has_length(3)))
        assert_that(ext_object, has_entry('CapabilityList',
                                          contains_inanyorder(
                                              'nti.platform.forums.dflforums',
                                              'nti.platform.forums.communityforums',
                                              'nti.platform.customization.can_change_password')))

    @mock_dataserver.WithMockDSTrans
    def test_external(self):
        user = User.create_user(dataserver=self.ds,
                                 username=u'sjohnson@nextthought.com')
        service = UserService(user)

        ext_object = toExternalObject(service)
        __traceback_info__ = ext_object
        # The user should have some capabilities
        assert_that(ext_object, has_entry('CapabilityList',
                                          has_item('nti.platform.p2p.chat')))
        assert_that(ext_object, has_entry('CapabilityList',
                                          has_item('nti.platform.p2p.sharing')))
        # The global workspace should have a Link
        workspaces = ext_object['Items']
        assert_that(workspaces,
                    has_item(has_entry('Title', 'Global')))

        # Catalog workspace
        catalog_ws = next(x for x in workspaces if x['Title'] == 'Catalog')
        assert_that(catalog_ws, not_none())
        catalog_collections = catalog_ws['Items']
        assert_that(catalog_collections, greater_than_or_equal_to(2))

        # Can't check links here, that comes from application configuration.
        # See test_usersearch.
        # And the User resource should have a Pages collection that also has
        # a link--this one pre-rendered
        user_ws = next(x for x in workspaces if x['Title'] == user.username)
        assert_that(user_ws, has_entry('Title', user.username))
        assert_that(user_ws,
                    has_entry('Items',
                             has_item(all_of(has_entry('Title', 'Pages'),
                                             has_entry('href', '/dataserver2/users/sjohnson@nextthought.com/Pages')))))
        for membership_name in ('FriendsLists', 'Groups', 'Communities', 'DynamicMemberships'):
            assert_that(user_ws,
                        has_entry('Items',
                                  has_item(all_of(has_entry('Title', membership_name),
                                                  has_entry('href', '/dataserver2/users/sjohnson@nextthought.com/' + membership_name)))))
        assert_that(user_ws,
                    has_entry('Items',
                             has_item(has_entry('Links', has_item(has_entry('Class', 'Link'))))))
        assert_that(user_ws['Items'],
                    has_item(has_entry('Links',
                                      has_item(has_entry('href',
                                                         '/dataserver2/users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData')))))

        assert_that(user_ws['Items'], has_item(has_entry('Title', 'Boards')))

        # And, if we have a site community, it's exposed.
        site_policy = component.queryUtility(ISitePolicyUserEventListener)
        site_policy.COM_USERNAME = 'community_username'
        ext_object = toExternalObject(service)
        assert_that(ext_object,
                    has_entry('SiteCommunity', 'community_username'))

    @mock_dataserver.WithMockDSTrans
    def test_user_pages_collection_accepts_only_external_types(self):
        #"A user's Pages collection only claims to accept things that are externally creatable."
        # We prove this via a negative, so unfortunately this is not such
        # a great test
        user = User.create_user(dataserver=self.ds,
                                username=u'sjohnson@nextthought.com')
        ws = UEW(user)
        assert_that('application/vnd.nextthought.transcriptsummary',
                    is_not(is_in(list(UserPagesCollection(ws).accepts))))
        assert_that('application/vnd.nextthought.canvasurlshape',
                    is_in(list(UserPagesCollection(ws).accepts)))
        assert_that('application/vnd.nextthought.bookmark',
                    is_in(list(UserPagesCollection(ws).accepts)))

    @mock_dataserver.WithMockDSTrans
    def test_user_pages_collection_restricted(self):
        user = User.create_user(dataserver=self.ds,
                                username=u'sjohnson@nextthought.com')
        ws = UEW(user)
        assert_that('application/vnd.nextthought.canvasurlshape',
                    is_in(list(UserPagesCollection(ws).accepts)))

        uew_ext = toExternalObject(ws)
        # And the blog, even though it's never been used
        assert_that(uew_ext['Items'], has_item(has_entry('Title', 'Blog')))

        # Making it ICoppaUser cuts that out
        interface.alsoProvides(user, ICoppaUserWithoutAgreement)
        assert_that('application/vnd.nextthought.canvasurlshape',
                    is_not(is_in(list(UserPagesCollection(ws).accepts))))

        # and from the vocab
        vocab = component.getUtility(IVocabularyFactory,
                                     "Creatable External Object Types")(user)
        terms = [x.token for x in vocab]
        assert_that('application/vnd.nextthought.canvasurlshape',
                    is_not(is_in(terms)))


class TestFriendsListContainerCollection(DataserverLayerTest, TestBaseMixin):

    @mock_dataserver.WithMockDSTrans
    def test_container_only_friends_list(self):
        owner_user, member_user, _member_user2, parent_dfl = _dfl_sharing_fixture(self.ds)

        owner_fl_cont = FriendsListContainerCollection(owner_user.friendsLists)
        assert_that(owner_fl_cont, has_property('container', has_length(0)))

        # The member container adds the DFL
        member_cont = FriendsListContainerCollection(member_user.friendsLists)
        assert_that(member_cont, has_property('container', has_length(0)))

        assert_that(member_cont.container,
                    has_property('__name__', owner_fl_cont.__name__))
        assert_that(member_cont.container,
                    has_property('__parent__', member_user))

        # Now, if we cheat and remove the member from the DFL, but leave the relationship
        # in place, then we handle that
        parent_dfl.removeFriend(member_user)
        member_user.record_dynamic_membership(parent_dfl)
        assert_that(list(parent_dfl), does_not(has_item(member_user)))
        assert_that(list(member_user.dynamic_memberships),
                    has_item(parent_dfl))

        assert_that(member_cont, has_property('container', has_length(0)))
