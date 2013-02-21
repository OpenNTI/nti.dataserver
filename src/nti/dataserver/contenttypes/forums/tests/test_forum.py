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

from zope import interface
import nti.tests
from Acquisition import Implicit
from nti.tests import aq_inContextOf
from nti.tests import verifiably_provides, validly_provides

from zope.container.interfaces import InvalidItemType, InvalidContainerType

from nti.dataserver.containers import CheckingLastModifiedBTreeContainer

from ..interfaces import IForum, ITopic
from ..forum import Forum


def test_forum_interfaces():
	post = Forum()
	assert_that( post, verifiably_provides( IForum ) )

	assert_that( post, validly_provides( IForum ) )

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
