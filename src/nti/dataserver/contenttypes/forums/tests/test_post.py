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
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_property
from hamcrest import has_entries
from hamcrest import none
from hamcrest import is_not
from hamcrest import all_of
from nose.tools import assert_raises


from nti.externalization.tests import externalizes
from nti.externalization.externalization import to_external_object
from nti.externalization import internalization

import nti.tests
from nti.tests import aq_inContextOf

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver.contenttypes.forums', 'nti.contentfragments') )
tearDownModule = nti.tests.module_teardown

from zope import interface
from nti.tests import verifiably_provides, validly_provides
from nti.tests import is_empty
from zope.container.interfaces import InvalidContainerType
from zope.mimetype.interfaces import IContentTypeAware
from nti.dataserver.containers import CheckingLastModifiedBTreeContainer
from ..interfaces import IPost, IPersonalBlogComment, ITopic
from ..post import Post, PersonalBlogComment, PersonalBlogEntryPost

from ExtensionClass import Base

def test_post_interfaces():
	post = Post()
	assert_that( post, verifiably_provides( IPost ) )

	assert_that( post, validly_provides( IPost ) )

	assert_that( Post, has_property( 'mime_type', 'application/vnd.nextthought.forums.post' ) )

def test_comment_interfaces():
	post = PersonalBlogComment()
	assert_that( post, verifiably_provides( IPersonalBlogComment ) )

	assert_that( post, validly_provides( IPersonalBlogComment ) )

	assert_that( PersonalBlogComment, has_property( 'mimeType', 'application/vnd.nextthought.forums.personalblogcomment' ) )


def test_comment_sharing_target_aq():

	class Parent(Base):
		sharingTargets = None
		child = None

	post = Parent()
	post.sharingTargets = set( ['a', 'b', 'c'] )
	child = PersonalBlogComment()
	child.__parent__ = post
	post.child = child

	assert_that( post.child, aq_inContextOf( post ) )
	assert_that( post.child.sharingTargets, is_( post.sharingTargets ) )

def test_blog_post_sharing_target_aq():

	class Parent(Base):
		sharingTargets = None
		child = None

	post = Parent()
	post.sharingTargets = set( ['a', 'b', 'c'] )
	child = PersonalBlogEntryPost()
	child.__parent__ = post # PARENT MUST BE SET FIRST
	post.child = child

	assert_that( post.child, aq_inContextOf( post ) )
	assert_that( post.child.sharingTargets, is_( post.sharingTargets ) )


def test_post_constraints():
	with assert_raises( InvalidContainerType ):
		container = CheckingLastModifiedBTreeContainer()
		container['k'] = Post()

	with assert_raises( InvalidContainerType ):
		container = CheckingLastModifiedBTreeContainer()
		container['k'] = PersonalBlogComment()

def test_post_externalizes():

	@interface.implementer(ITopic)
	class Parent(Base):
		NTIID = 'foo_bar_baz'

	parent = Parent()
	post = Post()
	post.title = 'foo'
	post.__parent__ = parent

	assert_that( post,
				 externalizes( all_of(
					 has_entries( 'title', 'foo',
								  'Class', 'Post',
								  'MimeType', 'application/vnd.nextthought.forums.post',
								  'body', none(),
								  'ContainerId', parent.NTIID,
								  'sharedWith', is_empty() ),
					is_not( has_key( 'flattenedSharingTargets' ) ) ) ) )

	ext_post = to_external_object( post )

	factory = internalization.find_factory_for( ext_post )
	new_post = factory()
	new_post.__parent__ = parent
	internalization.update_from_external_object( new_post, ext_post )

	assert_that( new_post, is_( post ) )



def test_comment_externalizes():

	post = PersonalBlogComment()
	post.title = 'foo'

	assert_that( post,
				 externalizes( all_of(
					 has_entries( 'title', 'foo',
								  'Class', 'PersonalBlogComment',
								  'MimeType', 'application/vnd.nextthought.forums.personalblogcomment',
								  'body', none(),
								  'sharedWith', is_empty() ),
					is_not( has_key( 'flattenedSharingTargets' ) ) ) ) )

	ext_post = to_external_object( post )

	factory = internalization.find_factory_for( ext_post )
	new_post = factory()
	internalization.update_from_external_object( new_post, ext_post )

	assert_that( new_post, is_( post ) )
