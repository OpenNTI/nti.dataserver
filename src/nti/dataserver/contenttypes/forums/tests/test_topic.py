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
from nose.tools import assert_raises
import nti.tests

import nti.tests
from zope.container.interfaces import InvalidItemType, InvalidContainerType
from nti.tests import verifiably_provides, validly_provides
from nti.dataserver.containers import CheckingLastModifiedBTreeContainer
from ..interfaces import ITopic, IStoryTopic
from ..topic import Topic, StoryTopic
from ..post import Post

def test_topic_interfaces():
	post = Topic()
	assert_that( post, verifiably_provides( ITopic ) )

	assert_that( post, validly_provides( ITopic ) )

def test_story_topic_interfaces():
	post = StoryTopic()
	assert_that( post, verifiably_provides( IStoryTopic ) )

	post.story = Post()
	assert_that( post, validly_provides( IStoryTopic ) )

def test_topic_constraints():

	topic = Topic()

	topic['k'] = Post()

	with assert_raises( InvalidItemType ):
		topic['z'] = Topic()


	with assert_raises( InvalidContainerType ):
		container = CheckingLastModifiedBTreeContainer()
		container['k'] = topic
