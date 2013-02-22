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

from ..interfaces import IBoard, IForum
from ..board import Board

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver.contenttypes.forums', 'nti.contentfragments') )
tearDownModule = nti.tests.module_teardown


def test_board_interfaces():
	post = Board()
	assert_that( post, verifiably_provides( IBoard ) )

	assert_that( post, validly_provides( IBoard ) )

def test_board_constraints():
	@interface.implementer(IForum)
	class Forum(Implicit):
		__parent__ = __name__ = None

	board = Board()
	# Allowed
	board['k'] = Forum()

	# And acquired
	assert_that( board['k'], aq_inContextOf( board ) )

	with assert_raises( InvalidItemType ):
		# Not allowed
		board['z'] = Board()

def test_blog_externalizes():

	post = Board()
	post.title = 'foo'
	post.description = 'the long\ndescription'

	@interface.implementer(IForum)
	class X(Implicit):
		__parent__ = __name__ = None

	assert_that( post,
				 externalizes( all_of(
					 has_entries( 'title', 'foo',
								  'description', 'the long\ndescription',
								  'Class', 'Board',
								  'MimeType', 'application/vnd.nextthought.forums.board',
								  'ForumCount', 0,
								  'sharedWith', is_empty() ),
					is_not( has_key( 'flattenedSharingTargets' ) ) ) ) )

	post['k'] = X()
	assert_that( post,
				 externalizes( has_entry( 'ForumCount', 1 ) ) )
