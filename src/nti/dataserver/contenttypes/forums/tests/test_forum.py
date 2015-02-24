#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import has_key
from hamcrest import all_of
from hamcrest import has_property
from hamcrest import same_instance
from hamcrest import is_not
from hamcrest import has_entries
from hamcrest import has_entry
from nose.tools import assert_raises

from zope import interface
from zope import component
from zope.container.interfaces import InvalidItemType, InvalidContainerType

from nti.testing.matchers import is_empty
from nti.utils._compat import Implicit
from nti.testing.matchers import aq_inContextOf
from nti.testing.matchers import verifiably_provides, validly_provides

from nti.externalization.tests import externalizes

from nti.dataserver.containers import CheckingLastModifiedBTreeContainer
from nti.dataserver.users import Community

from nti.wref.interfaces import IWeakRef

from ..interfaces import IForum, ITopic, IPersonalBlog, IGeneralForum, ICommunityForum
from ..interfaces import ICommunityBoard
from ..forum import Forum, PersonalBlog, GeneralForum, CommunityForum
from ..topic import PersonalBlogEntry

from . import ForumLayerTest

class TestForum(ForumLayerTest):

	def test_forum_interfaces(self):
		post = Forum()
		assert_that( post, verifiably_provides( IForum ) )

		assert_that( post, validly_provides( IForum ) )

	def test_general_forum_interfaces(self):
		post = GeneralForum()
		assert_that( post, verifiably_provides( IGeneralForum ) )

		assert_that( post, validly_provides( IGeneralForum ) )

	def test_community_forum_interfaces(self):
		post = CommunityForum()
		assert_that( post, verifiably_provides( ICommunityForum ) )

		assert_that( post, validly_provides( ICommunityForum ) )


	def test_blog_interfaces(self):
		post = PersonalBlog()
		assert_that( post, verifiably_provides( IForum ) )
		assert_that( post, validly_provides( IForum ) )
		assert_that( post, validly_provides( IPersonalBlog ) )
		assert_that( post, has_property( 'mimeType', 'application/vnd.nextthought.forums.personalblog'))
		assert_that( PersonalBlog, has_property( 'mimeType', 'application/vnd.nextthought.forums.personalblog'))

	def test_community_adapter(self):

		community = Community("foo")
		from zope.intid import IIntIds
		component.getUtility(IIntIds).register(community)
		forum = IGeneralForum(community)
		assert_that( forum, validly_provides( ICommunityForum ) )
		assert_that( forum, has_property( '__parent__', validly_provides( ICommunityBoard ) ) )
		assert_that( forum.__parent__, has_property( '__parent__', community ) )

	def test_forum_constraints(self):
		@interface.implementer(ITopic,IWeakRef)
		class X(Implicit):
			__parent__ = __name__ = None
			def __call__(self):
				return self
			def __iter__(self):
				return iter(())

		forum = Forum()
		forum['k'] = X()

		assert_that( forum['k'], aq_inContextOf( forum ) )
		# But the __parent__ is not aq wrapped
		assert_that( forum['k'], has_property( '__parent__', same_instance(forum) ) )

		with assert_raises( InvalidItemType ):
			forum['z'] = Forum()

		with assert_raises( InvalidContainerType ):
			container = CheckingLastModifiedBTreeContainer()
			container['k'] = forum

	def test_forum_container_multi_aq_wrap(self):
		# If we have something that is multiple levels
		# of wrapping, the __parent__s are still correct
		from ..board import Board
		from ..topic import Topic

		board = Board()
		forum = Forum()
		topic = Topic()


		board['forum'] = forum
		board['forum']['topic'] = topic

		# One level of access and we're fine
		assert_that( forum['topic'], has_property('__parent__',same_instance(forum) ) )
		assert_that( board['forum'], has_property('__parent__',same_instance(board) ) )

		# Because the __dict__ wound up with clean versions
		assert_that( topic.__dict__, has_entry( '__parent__', same_instance(forum) ) )
		assert_that( forum.__dict__, has_entry( '__parent__', same_instance(board) ) )

		# But multiple levels are wrapped
		# ExtensionClass doesn't wrap __parent__, but
		# Acquisition seems to. We workaround this in the container.
		assert_that( board['forum']['topic'],
					 has_property( '__parent__', same_instance(forum) ) )

	def test_blog_externalizes(self):

		blog = PersonalBlog()
		blog.title = 'foo'

		assert_that( blog,
					 externalizes( all_of(
						 has_entries( 'title', 'foo',
									  'Class', 'PersonalBlog',
									  'MimeType', 'application/vnd.nextthought.forums.personalblog',
									  'TopicCount', 0,
									  'sharedWith', is_empty() ),
						is_not( has_key( 'flattenedSharingTargets' ) ) ) ) )

		blog['k'] = PersonalBlogEntry()
		blog['k'].lastModified = 42
		blog['k'].createdTime = 24
		assert_that( blog,
					 externalizes( has_entries( 'TopicCount', 1,
												'NewestDescendantCreatedTime', 24,
												'NewestDescendant', has_entry('Class', 'PersonalBlogEntry') ) ) )

