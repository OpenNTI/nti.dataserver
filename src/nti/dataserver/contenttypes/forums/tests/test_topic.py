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
from hamcrest import starts_with
from hamcrest import not_none
from hamcrest import none
from hamcrest import has_property
from nose.tools import assert_raises
import nti.tests

import nti.tests

from nti.tests import is_empty

from nti.externalization.tests import externalizes

from nti.tests import aq_inContextOf
from zope.container.interfaces import InvalidItemType, InvalidContainerType, INameChooser
from nti.tests import verifiably_provides, validly_provides
from nti.dataserver.containers import CheckingLastModifiedBTreeContainer
from ..interfaces import ITopic, IHeadlineTopic, IPersonalBlogEntry, IGeneralHeadlineTopic, IPost
from ..topic import Topic, HeadlineTopic, PersonalBlogEntry, GeneralHeadlineTopic
from ..post import Post, HeadlinePost, PersonalBlogComment, PersonalBlogEntryPost, GeneralHeadlinePost

from ExtensionClass import Base

def setUpModule():
	nti.tests.module_setup( set_up_packages=('nti.dataserver.contenttypes.forums', 'nti.contentfragments', 'nti.dataserver') )
	# Set up weak refs
	from nti.intid import utility as intid_utility
	import zope.intid
	import zc.intid
	import BTrees
	from zope import component, interface
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

tearDownModule = nti.tests.module_teardown

def test_topic_interfaces():
	post = Topic()
	assert_that( post, verifiably_provides( ITopic ) )

	assert_that( post, validly_provides( ITopic ) )

def test_headline_topic_interfaces():
	topic = HeadlineTopic()
	assert_that( topic, verifiably_provides( IHeadlineTopic ) )

	topic.headline = HeadlinePost()
	assert_that( topic, validly_provides( IHeadlineTopic ) )
	assert_that( topic.headline, aq_inContextOf( topic ) )

def test_general_headline_topic_interfaces():
	topic = GeneralHeadlineTopic()
	assert_that( topic, verifiably_provides( IGeneralHeadlineTopic ) )

	topic.headline = GeneralHeadlinePost()
	assert_that( topic, validly_provides( IGeneralHeadlineTopic ) )
	assert_that( topic.headline, aq_inContextOf( topic ) )


def test_blog_entry():
	topic = PersonalBlogEntry()
	assert_that( topic, verifiably_provides( IPersonalBlogEntry ) )
	assert_that( topic, verifiably_provides( IHeadlineTopic ) )
	assert_that( topic, verifiably_provides( ITopic ) )

	headline = PersonalBlogEntryPost()
	headline.__parent__ = topic
	class Username(object):
		username = 'foo'
	headline.creator = Username()
	topic.creator = Username()
	topic.headline = headline
	assert_that( topic, validly_provides( IPersonalBlogEntry ) )
	assert_that( topic, validly_provides( IHeadlineTopic ) )
	assert_that( topic, validly_provides( ITopic ) )
	assert_that( topic.headline, aq_inContextOf( topic ) )

	# test acquisition
	class Parent(Base):
		pass

	parent = Parent()
	topic.__parent__ = parent
	parent.topic = topic

	assert_that( topic.headline, aq_inContextOf( parent ) )
	assert_that( topic, aq_inContextOf( parent ) )

def test_blog_entry_name_chooser():
	topic = PersonalBlogEntry()
	from ..forum import PersonalBlog
	blog = PersonalBlog()

	name = 'A name'
	assert_that( INameChooser( blog ).chooseName( name, topic ), is_( 'A_name' ) )
	blog['A_name'] = topic

	topic = PersonalBlogEntry()
	assert_that( INameChooser( blog ).chooseName( name, topic ), starts_with( 'A_name.' ) )

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
								  'NewestPost', none(),
								  'sharedWith', is_empty() ),
					is_not( has_key( 'flattenedSharingTargets' ) ) ) ) )

	# With a comment
	post['k'] = Post()
	post['k'].lastModified = 42
	# (Both cached in the ref)
	assert_that( post, has_property( '_newestPostWref', not_none() ) )
	assert_that( post,
				 externalizes( has_entries( 'PostCount', 1,
											'NewestPost', has_entries('Class','Post',
																	  'Last Modified', 42 ) ) ) )
	# and on-demand
	del post._newestPostWref
	assert_that( post, has_property( '_newestPostWref', none() ) )
	assert_that( post,
				 externalizes( has_entries( 'PostCount', 1,
											'NewestPost', has_entries('Class','Post',
																	  'Last Modified', 42 ) ) ) )



def test_blog_topic_externalizes():

	post = PersonalBlogEntry()
	post.title = 'foo'
	post.creator = 'me'

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
	post['k'].lastModified = 42
	assert_that( post,
				 externalizes( has_entries(
								'headline', has_entry( 'Class', 'PersonalBlogEntryPost' ),
					 			'PostCount', 1,
								'NewestPost', has_entry('Last Modified', 42) ) ) )
