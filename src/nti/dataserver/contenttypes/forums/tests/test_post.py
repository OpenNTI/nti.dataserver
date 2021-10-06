#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import all_of
from hamcrest import has_key
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_property

from nose.tools import assert_raises

from nti.testing.matchers import is_empty
from nti.testing.matchers import aq_inContextOf
from nti.testing.matchers import verifiably_provides, validly_provides

from zope import interface

from zope.container.interfaces import InvalidContainerType

from ExtensionClass import Base

from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.externalization import internalization
from nti.externalization.tests import externalizes
from nti.externalization import to_external_object

from nti.dataserver.contenttypes.forums.interfaces import IPost, IPersonalBlogComment, ITopic
from nti.dataserver.contenttypes.forums.post import Post, PersonalBlogComment, PersonalBlogEntryPost

from  nti.dataserver.contenttypes.forums.tests import ForumLayerTest

class TestPost(ForumLayerTest):

	def test_post_interfaces(self):
		post = Post()
		assert_that(post, verifiably_provides(IPost))
		assert_that(post, validly_provides(IPost))
		assert_that(Post, has_property('mime_type', 'application/vnd.nextthought.forums.post'))

	def test_comment_interfaces(self):
		post = PersonalBlogComment()
		assert_that(post, verifiably_provides(IPersonalBlogComment))
		assert_that(post, validly_provides(IPersonalBlogComment))
		assert_that(PersonalBlogComment, has_property('mimeType', 'application/vnd.nextthought.forums.personalblogcomment'))

	def test_comment_sharing_target_aq(self):

		class Parent(Base):
			sharingTargets = None
			child = None

		post = Parent()
		post.sharingTargets = set(['a', 'b', 'c'])
		child = PersonalBlogComment()
		child.__parent__ = post
		post.child = child

		assert_that(post.child, aq_inContextOf(post))
		assert_that(post.child.sharingTargets, is_(post.sharingTargets))

	def test_blog_post_sharing_target_aq(self):

		class Parent(Base):
			sharingTargets = None
			child = None

		post = Parent()
		post.sharingTargets = set(['a', 'b', 'c'])
		child = PersonalBlogEntryPost()
		child.__parent__ = post  # PARENT MUST BE SET FIRST
		post.child = child

		assert_that(post.child, aq_inContextOf(post))
		assert_that(post.child.sharingTargets, is_(post.sharingTargets))

	def test_post_constraints(self):
		with assert_raises(InvalidContainerType):
			container = CheckingLastModifiedBTreeContainer()
			container['k'] = Post()

		with assert_raises(InvalidContainerType):
			container = CheckingLastModifiedBTreeContainer()
			container['k'] = PersonalBlogComment()

	def test_post_derived_containerId(self):

		@interface.implementer(ITopic)
		class Parent(Base):
			pass

		parent = Parent()
		parent.NTIID = 'foo_bar_baz'
		post = Post()
		post.title = 'foo'
		post.__parent__ = parent

		assert_that(post.containerId, is_(parent.NTIID))
		del parent.NTIID
		with assert_raises(AttributeError):
			post.containerId

		post.__dict__['containerId'] = 1  # Legacy
		assert_that(post.containerId, is_(1))

		from .. import _CreatedNamedNTIIDMixin
		class Parent2(_CreatedNamedNTIIDMixin):
			username = None
			@property
			def _ntiid_creator_username(self):
				return self.username
			_ntiid_type = 'baz'

		post.__parent__ = Parent2()
		assert_that(post.containerId, is_(None))
		post.__parent__.username = 'foo'
		assert_that(post.containerId, is_('tag:nextthought.com,2011-10:foo-baz'))
		post.__parent__.username = 'foo2'
		assert_that(post.containerId, is_('tag:nextthought.com,2011-10:foo2-baz'))

		post.__parent__.__name__ = 'local'
		assert_that(post.containerId, is_('tag:nextthought.com,2011-10:foo2-baz-local'))

	def test_post_externalizes(self):

		@interface.implementer(ITopic)
		class Parent(Base):
			NTIID = 'foo_bar_baz'

		parent = Parent()
		post = Post()
		post.title = 'foo'
		post.__parent__ = parent

		assert_that(post,
					 externalizes(all_of(
						 has_entries( 'title', 'foo',
									  'Class', 'Post',
									  'MimeType', 'application/vnd.nextthought.forums.post',
									  'body', none(),
									  'ContainerId', parent.NTIID,
									  'sharedWith', is_empty()),
						is_not(has_key('flattenedSharingTargets')))))

		ext_post = to_external_object(post)

		factory = internalization.find_factory_for(ext_post)
		new_post = factory()
		new_post.__parent__ = parent
		internalization.update_from_external_object(new_post, ext_post)

		assert_that(new_post, is_(post))

	def test_comment_externalizes(self):

		post = PersonalBlogComment()
		post.title = 'foo'

		assert_that(post,
					 externalizes(all_of(
						 has_entries( 'title', 'foo',
									  'Class', 'PersonalBlogComment',
									  'MimeType', 'application/vnd.nextthought.forums.personalblogcomment',
									  'body', none(),
									  'sharedWith', is_empty(),
									  'references', [],
									  'inReplyTo', None),
						is_not(has_key('flattenedSharingTargets')))))

		ext_post = to_external_object(post)
		factory = internalization.find_factory_for(ext_post)
		new_post = factory()
		internalization.update_from_external_object(new_post, ext_post)
		assert_that(new_post, is_(post))
		# Validate encoding
		body1 = u'Aquí está/están'
		body2 = u'သင့်ရဲ့ Learning Goal တွေကို ပြန်ပုံဖော်ကြည့်ပါ။ သင် ဘယ် Goal တွေကို အကောင်အထည်ဖော်ပြီးပြီလဲ ?'
		for body in (body1, body2):
			ext_post['body'] = [body]
			factory = internalization.find_factory_for(ext_post)
			new_post = factory()
			internalization.update_from_external_object(new_post, ext_post)
