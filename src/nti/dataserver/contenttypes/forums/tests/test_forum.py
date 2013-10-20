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
import nti.testing.base
from nti.testing.matchers import is_empty
from Acquisition import Implicit
from nti.testing.matchers import aq_inContextOf
from nti.testing.matchers import verifiably_provides, validly_provides

from nti.externalization.tests import externalizes
from zope.container.interfaces import InvalidItemType, InvalidContainerType

from nti.dataserver.containers import CheckingLastModifiedBTreeContainer
from nti.dataserver.users import Community


from ..interfaces import IForum, ITopic, IPersonalBlog, IPersonalBlogEntry, IGeneralForum, ICommunityForum, IPost
from ..interfaces import ICommunityBoard
from ..forum import Forum, PersonalBlog, GeneralForum, CommunityForum
from ..topic import PersonalBlogEntry

from nti.wref.interfaces import IWeakRef

def setUpModule():
	nti.testing.base.module_setup( set_up_packages=(('subscribers.zcml', 'nti.intid'), 'nti.dataserver.contenttypes.forums', 'nti.contentfragments', 'zope.annotation',) )

	# Set up weak refs
	from nti.intid import utility as intid_utility
	import zope.intid
	import zc.intid
	import BTrees
	from zope import component
	from zope.keyreference.interfaces import IKeyReference
	intids = intid_utility.IntIds('_ds_intid', family=BTrees.family64 )
	intids.__name__ = '++etc++intids'
	component.provideUtility( intids, provides=zope.intid.IIntIds )
	# Make sure to register it as both types of utility, one is a subclass of the other
	component.provideUtility( intids, provides=zc.intid.IIntIds )

	@interface.implementer(IKeyReference)
	@component.adapter(IPost)
	class CommentKeyRef(object):
		def __init__( self, context ):
			pass

	component.provideAdapter(CommentKeyRef)
	component.provideAdapter(CommentKeyRef, adapts=(IPersonalBlogEntry,) )

	from nti.dataserver.tests import mock_redis
	client = mock_redis.InMemoryMockRedis()
	component.provideUtility( client )

tearDownModule = nti.testing.base.module_teardown


def test_forum_interfaces():
	post = Forum()
	assert_that( post, verifiably_provides( IForum ) )

	assert_that( post, validly_provides( IForum ) )

def test_general_forum_interfaces():
	post = GeneralForum()
	assert_that( post, verifiably_provides( IGeneralForum ) )

	assert_that( post, validly_provides( IGeneralForum ) )

def test_community_forum_interfaces():
	post = CommunityForum()
	assert_that( post, verifiably_provides( ICommunityForum ) )

	assert_that( post, validly_provides( ICommunityForum ) )


def test_blog_interfaces():
	post = PersonalBlog()
	assert_that( post, verifiably_provides( IForum ) )
	assert_that( post, validly_provides( IForum ) )
	assert_that( post, validly_provides( IPersonalBlog ) )

def test_community_adapter():

	community = Community("foo")

	forum = IGeneralForum(community)
	assert_that( forum, validly_provides( ICommunityForum ) )
	assert_that( forum, has_property( '__parent__', validly_provides( ICommunityBoard ) ) )
	assert_that( forum.__parent__, has_property( '__parent__', community ) )

def test_forum_constraints():
	@interface.implementer(ITopic,IWeakRef)
	class X(Implicit):
		__parent__ = __name__ = None
		def __call__(self):
			return self

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

def test_forum_container_multi_aq_wrap():
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
	assert_that( board['forum']['topic'],
				 has_property( '__parent__', is_not( same_instance(forum) ) ) )

def test_blog_externalizes():

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
