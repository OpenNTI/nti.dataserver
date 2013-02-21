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
from hamcrest import all_of
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entries
from hamcrest import has_entry
from nose.tools import assert_raises

from zope import interface
import nti.tests
from nti.tests import is_empty
from Acquisition import Implicit
from nti.tests import aq_inContextOf
from nti.tests import verifiably_provides, validly_provides

from nti.externalization.tests import externalizes
from zope.container.interfaces import InvalidItemType, InvalidContainerType

from nti.dataserver.containers import CheckingLastModifiedBTreeContainer


setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver.contenttypes.forums', 'nti.contentfragments') )
tearDownModule = nti.tests.module_teardown


from ..interfaces import IForum, ITopic, IPersonalBlog, IStoryTopic
from ..forum import Forum, PersonalBlog


def test_forum_interfaces():
	post = Forum()
	assert_that( post, verifiably_provides( IForum ) )

	assert_that( post, validly_provides( IForum ) )


def test_blog_interfaces():
	post = PersonalBlog()
	assert_that( post, verifiably_provides( IForum ) )
	assert_that( post, validly_provides( IForum ) )
	assert_that( post, validly_provides( IPersonalBlog ) )

def test_forum_constraints():
	@interface.implementer(ITopic)
	class X(Implicit):
		__parent__ = __name__ = None

	forum = Forum()
	forum['k'] = X()

	assert_that( forum['k'], aq_inContextOf( forum ) )

	with assert_raises( InvalidItemType ):
		forum['z'] = Forum()

	with assert_raises( InvalidContainerType ):
		container = CheckingLastModifiedBTreeContainer()
		container['k'] = forum


def test_blog_externalizes():

	post = PersonalBlog()
	post.title = 'foo'

	@interface.implementer(IStoryTopic)
	class X(Implicit):
		__parent__ = __name__ = None

	assert_that( post,
				 externalizes( all_of(
					 has_entries( 'title', 'foo',
								  'Class', 'PersonalBlog',
								  'MimeType', 'application/vnd.nextthought.forums.personalblog',
								  'TopicCount', 0,
								  'sharedWith', is_empty() ),
					is_not( has_key( 'flattenedSharingTargets' ) ) ) ) )

	post['k'] = X()
	assert_that( post,
				 externalizes( has_entry( 'TopicCount', 1 ) ) )
