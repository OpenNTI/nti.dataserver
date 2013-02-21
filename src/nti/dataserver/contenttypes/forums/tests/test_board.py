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
from zope.container.interfaces import InvalidItemType
from nti.tests import verifiably_provides, validly_provides

from ..interfaces import IBoard, IForum
from ..board import Board


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
