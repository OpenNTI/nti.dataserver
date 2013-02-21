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
from ..interfaces import ITopic, IStoryTopic
from ..topic import Topic, StoryTopic
from ..post import Post


setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver.contenttypes.forums', 'nti.contentfragments') )
tearDownModule = nti.tests.module_teardown

def test_topic_interfaces():
	post = Topic()
	assert_that( post, verifiably_provides( ITopic ) )

	assert_that( post, validly_provides( ITopic ) )

def test_story_topic_interfaces():
	topic = StoryTopic()
	assert_that( topic, verifiably_provides( IStoryTopic ) )

	topic.story = Post()
	assert_that( topic, validly_provides( IStoryTopic ) )
	assert_that( topic.story, aq_inContextOf( topic ) )

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

	post = StoryTopic()
	post.title = 'foo'

	assert_that( post,
				 externalizes( all_of(
					 has_entries( 'title', 'foo',
								  'Class', 'StoryTopic',
								  'MimeType', 'application/vnd.nextthought.forums.storytopic',
								  'PostCount', 0,
								  'sharedWith', is_empty() ),
					is_not( has_key( 'flattenedSharingTargets' ) ) ) ) )

	post['k'] = Post()
	assert_that( post,
				 externalizes( has_entry( 'PostCount', 1 ) ) )
