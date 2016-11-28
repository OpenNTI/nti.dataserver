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
from nose.tools import assert_raises

from nti.dataserver import liking

import unittest

class TestLiking(unittest.TestCase):

	def test_favorite_safe(self):

		with assert_raises(TypeError):
			liking.favorites_object( object(), 'foo' )

		assert_that( liking.favorites_object( object(), 'foo', safe=True ), is_( False ) )
