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
from hamcrest import has_entry
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_entries
from nose.tools import assert_raises
import nti.tests

import nti.tests

from nti.tests import is_empty

from nti.externalization.tests import externalizes

from nti.tests import aq_inContextOf
from zope.container.interfaces import InvalidItemType, InvalidContainerType
from nti.tests import verifiably_provides, validly_provides
from nti.dataserver.containers import CheckingLastModifiedBTreeContainer
from ..interfaces import ITopic, IHeadlineTopic, IPersonalBlogEntry
from ..topic import Topic, HeadlineTopic, PersonalBlogEntry
from ..post import Post, HeadlinePost, PersonalBlogComment, PersonalBlogEntryPost

from ExtensionClass import Base

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver.contenttypes.forums', 'nti.contentfragments') )
tearDownModule = nti.tests.module_teardown

def test_topic_interfaces():
	post = Topic()
	assert_that( post, verifiably_provides( ITopic ) )

	assert_that( post, validly_provides( ITopic ) )

def test_story_topic_interfaces():
	topic = HeadlineTopic()
	assert_that( topic, verifiably_provides( IHeadlineTopic ) )

	topic.headline = HeadlinePost()
	assert_that( topic, validly_provides( IHeadlineTopic ) )
	assert_that( topic.headline, aq_inContextOf( topic ) )


def test_blog_entry():
	topic = PersonalBlogEntry()
	assert_that( topic, verifiably_provides( IPersonalBlogEntry ) )
	assert_that( topic, verifiably_provides( IHeadlineTopic ) )
	assert_that( topic, verifiably_provides( ITopic ) )

	headline = PersonalBlogEntryPost()
	headline.__parent__ = topic
	topic.headline = headline
	assert_that( topic, validly_provides( IPersonalBlogEntry ) )
	assert_that( topic, validly_provides( IHeadlineTopic ) )
	assert_that( topic, validly_provides( ITopic ) )
	assert_that( topic.headline, aq_inContextOf( topic ) )

	# sharing targets are inherited all the way down
	class Parent(Base):
		sharingTargets = ()

	parent = Parent()
	parent.sharingTargets = set( [1, 2, 3] )
	topic.__parent__ = parent
	parent.topic = topic

	assert_that( topic.headline, aq_inContextOf( parent ) )
	assert_that( topic, aq_inContextOf( parent ) )

	assert_that( topic.sharingTargets, is_( parent.sharingTargets ) )

	assert_that( parent.topic.headline.sharingTargets, is_( parent.sharingTargets ) )

def test_topic_constraints():

	topic = Topic()

	topic['k'] = Post()
	assert_that( topic['k'], aq_inContextOf( topic ) )

	with assert_raises( InvalidItemType ):
		topic['z'] = Topic()


	with assert_raises( InvalidContainerType ):
		container = CheckingLastModifiedBTreeContainer()
		container['k'] = topic


def test_story_topic_externalizes():

	post = HeadlineTopic()
	post.title = 'foo'

	assert_that( post,
				 externalizes( all_of(
					 has_entries( 'title', 'foo',
								  'Class', 'HeadlineTopic',
								  'MimeType', 'application/vnd.nextthought.forums.headlinetopic',
								  'PostCount', 0,
								  'sharedWith', is_empty() ),
					is_not( has_key( 'flattenedSharingTargets' ) ) ) ) )

	post['k'] = Post()
	assert_that( post,
				 externalizes( has_entry( 'PostCount', 1 ) ) )



def test_blog_topic_externalizes():

	post = PersonalBlogEntry()
	post.title = 'foo'

	assert_that( post,
				 externalizes( all_of(
					 has_entries( 'title', 'foo',
								  'Class', 'PersonalBlogEntry',
								  'MimeType', 'application/vnd.nextthought.forums.personalblogentry',
								  'PostCount', 0,
								  'sharedWith', is_empty() ),
					is_not( has_key( 'flattenedSharingTargets' ) ) ) ) )

	post.headline = PersonalBlogEntryPost()
	post['k'] = PersonalBlogComment()
	assert_that( post,
				 externalizes( has_entries(
								'headline', has_entry( 'Class', 'PersonalBlogEntryPost' ),
					 			'PostCount', 1 ) ) )
