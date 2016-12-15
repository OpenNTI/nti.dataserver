#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import raises
from hamcrest import calling
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import starts_with
from hamcrest import has_property
does_not = is_not

from nose.tools import assert_raises

from nti.testing.matchers import aq_inContextOf
from nti.testing.matchers import is_empty, is_true
from nti.testing.matchers import verifiably_provides, validly_provides

import fudge

from zope import component
from zope import interface

from zope.container.interfaces import InvalidItemType, InvalidContainerType, INameChooser

from zope.intid import IIntIds

from zope.schema.interfaces import ConstraintNotSatisfied

from ExtensionClass import Base

from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.externalization.internalization import update_from_external_object

from nti.dataserver.interfaces import IUser, IWritableShared, IPrincipal

from nti.dataserver.contenttypes.forums.interfaces import ITopic, IHeadlineTopic
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry, IGeneralHeadlineTopic

from nti.dataserver.contenttypes.forums.topic import Topic, HeadlineTopic, PersonalBlogEntry
from nti.dataserver.contenttypes.forums.topic import DFLHeadlineTopic, GeneralHeadlineTopic, CommunityHeadlineTopic

from nti.dataserver.contenttypes.forums.post import Post, HeadlinePost, PersonalBlogComment
from nti.dataserver.contenttypes.forums.post import PersonalBlogEntryPost, GeneralHeadlinePost

from nti.dataserver.contenttypes.forums.tests import ForumLayerTest

from nti.externalization.tests import externalizes

from nti.dataserver.tests import mock_dataserver

class TestTopic(ForumLayerTest):

	def test_topic_interfaces(self):
		post = Topic()
		assert_that(post, verifiably_provides(ITopic))
		assert_that(post, validly_provides(ITopic))

	def test_headline_topic_interfaces(self):
		topic = HeadlineTopic()
		assert_that(topic, verifiably_provides(IHeadlineTopic))

		topic.headline = HeadlinePost()
		assert_that(topic, validly_provides(IHeadlineTopic))
		assert_that(topic.headline, aq_inContextOf(topic))

	def test_general_headline_topic_interfaces(self):
		topic = GeneralHeadlineTopic()
		assert_that(topic, verifiably_provides(IGeneralHeadlineTopic))

		topic.headline = GeneralHeadlinePost()
		assert_that(topic, validly_provides(IGeneralHeadlineTopic))
		assert_that(topic.headline, aq_inContextOf(topic))

	def test_blog_entry(self):
		topic = PersonalBlogEntry()
		assert_that(topic, verifiably_provides(IPersonalBlogEntry))
		assert_that(topic, verifiably_provides(IHeadlineTopic))
		assert_that(topic, verifiably_provides(ITopic))

		headline = PersonalBlogEntryPost()
		headline.__parent__ = topic
		@interface.implementer(IPrincipal)
		class Username(object):
			id = username = 'foo'

		headline.creator = Username()
		topic.creator = Username()
		topic.headline = headline
		assert_that(topic, validly_provides(IPersonalBlogEntry))
		assert_that(topic, validly_provides(IHeadlineTopic))
		assert_that(topic, validly_provides(ITopic))
		assert_that(topic.headline, aq_inContextOf(topic))

		# test acquisition
		class Parent(Base):
			pass

		parent = Parent()
		topic.__parent__ = parent
		parent.topic = topic

		assert_that(topic.headline, aq_inContextOf(parent))
		assert_that(topic, aq_inContextOf(parent))

	@fudge.patch('nti.dataserver.sharing._dynamic_memberships_that_participate_in_security',
				 'nti.dataserver.sharing._getId')
	def test_blog_entry_sharing(self, fake_mems, fake_getId):
		fake_mems.is_callable().returns((1, 2, 3))
		fake_getId.is_callable().returns(1)

		@interface.implementer(IUser)
		class Creator(object):
			pass

		# Default state
		topic = PersonalBlogEntry()
		topic.creator = Creator()
		assert_that(topic, verifiably_provides(IWritableShared))
		assert_that(topic, has_property('sharingTargets', is_empty()))

		# Published
		topic.publish()
		assert_that(topic, does_not(verifiably_provides(IWritableShared)))
		assert_that(topic, has_property('sharingTargets', is_((1, 2, 3))))

		# Updating sharing targets is ignored
		topic.updateSharingTargets((4, 5, 6))
		topic.clearSharingTargets()
		assert_that(topic, has_property('sharingTargets', is_((1, 2, 3))))

		topic.unpublish()
		# Now we can, though
		topic.updateSharingTargets((42,))
		assert_that(topic._may_have_sharing_targets(), is_true())

	def test_blog_entry_name_chooser(self):
		topic = PersonalBlogEntry()
		from nti.dataserver.contenttypes.forums.forum import PersonalBlog
		blog = PersonalBlog()

		name = 'A name'
		assert_that(INameChooser(blog).chooseName(name, topic), is_('A_name'))
		blog['A_name'] = topic

		topic = PersonalBlogEntry()
		assert_that(INameChooser(blog).chooseName(name, topic), starts_with('A_name.'))

	def test_topic_constraints(self):

		topic = Topic()

		topic['k'] = Post()
		assert_that(topic['k'], aq_inContextOf(topic))

		with assert_raises(InvalidItemType):
			topic['z'] = Topic()

		with assert_raises(InvalidContainerType):
			container = CheckingLastModifiedBTreeContainer()
			container['k'] = topic

	def test_headline_topic_externalizes(self):

		topic = HeadlineTopic()
		topic.title = 'foo'

		assert_that(topic,
					 externalizes(all_of(
						has_entries('title', 'foo',
									'Class', 'HeadlineTopic',
									'MimeType', 'application/vnd.nextthought.forums.headlinetopic',
									'PostCount', 0,
									'NewestDescendant', none(),
									'sharedWith', is_empty()),
						is_not(has_key('flattenedSharingTargets')))))

		assert_that(calling(update_from_external_object).with_args(topic, {'title': 'No\nnewline'}),
					raises(ConstraintNotSatisfied, "(u'No\\\\nnewline', u'title')"))

		# With a comment
		topic['k'] = Post()
		topic['k'].lastModified = 42
		# (Both cached in the ref)
		assert_that(topic, has_property('_newestPostWref', not_none()))
		assert_that(topic,
					 externalizes(has_entries('PostCount', 1,
											  'NewestDescendant', has_entries('Class', 'Post',
																		  'Last Modified', 42))))
		# and on-demand
		del topic._newestPostWref
		assert_that(topic, has_property('_newestPostWref', none()))
		assert_that(topic,
					 externalizes(has_entries('PostCount', 1,
											  'NewestDescendant', has_entries('Class', 'Post',
																		  'Last Modified', 42))))
	def test_blog_topic_externalizes(self):

		post = PersonalBlogEntry()
		post.title = 'foo'
		post.creator = 'me'

		assert_that(post,
					 externalizes(all_of(
						has_entries('title', 'foo',
									'Class', 'PersonalBlogEntry',
									'MimeType', 'application/vnd.nextthought.forums.personalblogentry',
									'PostCount', 0,
									'sharedWith', is_empty()),
						is_not(has_key('flattenedSharingTargets')))))

		post.headline = PersonalBlogEntryPost()
		post['k'] = PersonalBlogComment()
		post['k'].lastModified = 42
		assert_that(post,
					externalizes(has_entries(
									'headline', has_entry('Class', 'PersonalBlogEntryPost'),
									'PostCount', 1,
									'NewestDescendant', has_entry('Last Modified', 42))))
		
	def test_most_recent_reply(self):
		
		# If no comments on a topic, we should get nothing back. 
		topic = Topic()
		assert_that(topic.mostRecentReply, is_([]))
		
		# If we have a top-level comment, we should get it back.
		top_level_post = Post()
		top_level_post.inReplyTo = None
		topic['k'] = top_level_post
		assert_that(topic.mostRecentReply, is_(top_level_post))

		# A newer top-level comment should come back if present		
		newer_post = Post()
		newer_post.inReplyTo = None
		topic['l'] = newer_post
		assert_that(topic.mostRecentReply, is_(newer_post))

		# Replying to an existing comment should not
		# affect what we get back.
		non_top_level_post = Post()
		non_top_level_post.inReplyTo = top_level_post
		topic['m']= non_top_level_post
		assert_that(topic.mostRecentReply, is_(newer_post))

from nti.dataserver.users import Community

from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.dataserver.contenttypes.forums.tests import DataserverLayerTest

class TestCommunityTopicNTIIDResolver(DataserverLayerTest):

	def _do_test(self, forum_name, topic_name):

		with mock_dataserver.mock_db_trans(self.ds):
			comm = Community.create_community(self.ds, username="CHEM4970.ou.nextthought.com")

			board = ICommunityBoard(comm)

			forum = CommunityForum()
			forum.title = 'test'

			board[forum_name] = forum

			topic = CommunityHeadlineTopic()
			topic.title = 'a test'
			topic.creator = 'me'

			forum[topic_name] = topic

			assert_that(topic.NTIID, is_('tag:nextthought.com,2011-10:CHEM4970.ou.nextthought.com-Topic:GeneralCommunity-' + forum_name + '.' + topic_name))
			assert_that(find_object_with_ntiid(topic.NTIID), is_(topic))

	@mock_dataserver.WithMockDS
	def test_forum_name_unique(self):
		self._do_test('test.68574', 'test')

	@mock_dataserver.WithMockDS
	def test_topic_name_unique(self):
		self._do_test('test', 'test.6854')

	@mock_dataserver.WithMockDS
	def test_both_name_unique(self):
		self._do_test('test.6854', 'test.6854')

	@mock_dataserver.WithMockDS
	def test_neither_name_unique(self):
		self._do_test('test', 'test')

from nti.dataserver.users import User
from nti.dataserver.users import DynamicFriendsList

from nti.dataserver.contenttypes.forums.forum import DFLForum
from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard

class TestDFLTopicNTIIDResolver(DataserverLayerTest):

	def _do_test(self, forum_name, topic_name):

		with mock_dataserver.mock_db_trans(self.ds):
			ichigo = User.create_user(self.ds, username="ichigo@bleach.com")
			bleach = DynamicFriendsList(username='bleach')
			bleach.creator = ichigo  # Creator must be set
			ichigo.addContainedObject(bleach)
			
			board = IDFLBoard(bleach)

			forum = DFLForum()
			forum.title = 'test'
			board[forum_name] = forum

			topic = DFLHeadlineTopic()
			topic.title = 'a test'
			topic.creator = 'me'

			forum[topic_name] = topic
			intids = component.getUtility(IIntIds)
			intid = intids.getId(bleach)
			
			ntiid = 'tag:nextthought.com,2011-10:%s-Topic:GeneralDFL-%s.%s' % (intid, forum_name, topic_name)
			assert_that(topic.NTIID, is_(ntiid))
			assert_that(find_object_with_ntiid(topic.NTIID), is_(topic))

	@mock_dataserver.WithMockDS
	def test_forum_name_unique(self):
		self._do_test('test.68574', 'test')

	@mock_dataserver.WithMockDS
	def test_topic_name_unique(self):
		self._do_test('test', 'test.6854')

	@mock_dataserver.WithMockDS
	def test_both_name_unique(self):
		self._do_test('test.6854', 'test.6854')

	@mock_dataserver.WithMockDS
	def test_neither_name_unique(self):
		self._do_test('test', 'test')
