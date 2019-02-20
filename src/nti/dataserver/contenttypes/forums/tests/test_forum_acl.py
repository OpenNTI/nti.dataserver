#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import instance_of

from nti.testing.matchers import verifiably_provides, validly_provides

from zope import interface

from zope.security.interfaces import IPrincipal

from nti.dataserver.users import Community
from nti.dataserver.interfaces import IACLProvider
from nti.dataserver.interfaces import ACE_ACT_ALLOW
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.dataserver.contenttypes.forums.interfaces import ICommunityAdminRestrictedForum
from nti.dataserver.contenttypes.forums.interfaces import IForumACE
from nti.dataserver.contenttypes.forums.interfaces import IACLCommunityForum
from nti.dataserver.contenttypes.forums.interfaces import IACLCommunityBoard

from nti.dataserver.contenttypes.forums.ace import ForumACE

from nti.dataserver.contenttypes.forums.board import CommunityBoard

from nti.dataserver.contenttypes.forums.forum import ACLCommunityForum

from nti.dataserver.contenttypes.forums.acl import _ACLCommunityForumACLProvider
from nti.dataserver.contenttypes.forums.acl import _ACLCommunityAdminRestrictedForumACLProvider

from . import ForumLayerTest

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

class TestForumACL(ForumLayerTest):

	def test_acl_forum_interfaces(self):
		forum = ACLCommunityForum()
		assert_that(forum, verifiably_provides(IACLCommunityForum))
		assert_that(forum, validly_provides(IACLCommunityForum))

	def test_forum_ace_interfaces(self):
		ace = ForumACE()
		assert_that(ace, verifiably_provides(IForumACE))

	def test_forum_iter(self):
		ace = ForumACE(Action='Allow', Permissions=('Read', 'Create'), Entities=('foo', 'foo2'))
		assert_that(list(ace), has_length(4))

	def test_forum_acl_provider(self):
		forum = ACLCommunityForum()
		provider = nti_interfaces.IACLProvider(forum)
		assert_that(provider, instance_of(_ACLCommunityForumACLProvider))

		from IPython.terminal.debugger import set_trace;set_trace()

		interface.alsoProvides(forum, ICommunityAdminRestrictedForum)
		provider = nti_interfaces.IACLProvider(forum)
		assert_that(provider, instance_of(_ACLCommunityAdminRestrictedForumACLProvider))

	def test_externalizes(self):
		ace = ForumACE(Action='Allow', Permissions=('All',), Entities=('foo',))
		forum = ACLCommunityForum()
		forum.ACL = [ace]
		external = toExternalObject(forum)
		assert_that(external, has_entry('Class', u'CommunityForum'))
		assert_that(external, has_entry('MimeType', u'application/vnd.nextthought.forums.communityforum'))
		assert_that(external, has_entry('ACL', has_length(1)))
		ace_external = external['ACL'][0]
		assert_that(ace_external,
					has_entries('Action', u'Allow',
								'Class', 'ForumACE',
								'Entities', [u'foo'],
								'MimeType', u'application/vnd.nextthought.forums.ace',
								'Permissions', [u'All']))

		factory = find_factory_for(ace_external)
		new_ace = factory()
		update_from_external_object(new_ace, ace_external)
		assert_that(ace, is_(new_ace))

class TestBoardACL(DataserverLayerTest):

	@WithMockDSTrans
	def test_acl_from_ntiid_of_community(self):
		board = CommunityBoard()
		self.ds.root_folder['board'] = board
		community = Community.create_community(dataserver=self.ds, username='TestCommunity')
		creator = Community.create_community(dataserver=self.ds, username='Creator')

		com_ntiid = community.NTIID
		assert_that(com_ntiid, is_('tag:nextthought.com,2011-10:system-NamedEntity:Community-testcommunity'))

		ace = ForumACE(Action='Allow',
					   Permissions=('Read',),
					   Entities=(com_ntiid,))
		board.ACL = [ace]
		board.creator = creator

		interface.alsoProvides(board, IACLCommunityBoard)

		prov = IACLProvider(board)
		acl = prov.__acl__

		assert_that(list(acl[-2])[:2],
					 is_([ACE_ACT_ALLOW, IPrincipal(community)]))
