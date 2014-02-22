#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id: test_forum.py 21359 2013-07-26 05:23:32Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import instance_of
from hamcrest import is_


from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from ..interfaces import IForumACE
from ..interfaces import IACLCommunityForum

from ..ace import ForumACE
from ..forum import ACLCommunityForum
from ..acl import _ACLCommunityForumACLProvider

from nti.testing.matchers import verifiably_provides, validly_provides

from . import ForumLayerTest

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
