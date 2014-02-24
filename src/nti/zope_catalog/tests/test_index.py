#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_property
from hamcrest import calling
from hamcrest import raises
from hamcrest import contains

from nti.testing import base
from nti.testing import matchers

import BTrees

from ..field import CaseInsensitiveAttributeFieldIndex
from ..field import IntegerAttributeIndex

class TestCaseInsensitiveAttributeIndex(unittest.TestCase):

	field = 'VALUE'

	def setUp(self):
		super(TestCaseInsensitiveAttributeIndex,self).setUp()
		self.index = CaseInsensitiveAttributeFieldIndex('field')

	def test_family(self):
		assert_that( self.index, has_property('family',
											  BTrees.family64) )

	def test_noramlize_on_index(self):
		self.index.index_doc( 1, self)
		assert_that( self.index._fwd_index, has_key('value'))


class TestIntegerAttributeIndex(unittest.TestCase):

	field = 1234

	def setUp(self):
		super(TestIntegerAttributeIndex,self).setUp()
		self.index = IntegerAttributeIndex('field')

	def test_family(self):
		assert_that( self.index, has_property('family',
											  BTrees.family64) )
		assert_that( self.index, has_property('_rev_index',
											  is_(BTrees.family64.II.BTree)))
		assert_that( self.index, has_property('_fwd_index',
											  is_(BTrees.family64.IO.BTree)))

	def test_index_wrong_value(self):
		self.field = 'str'

		assert_that( calling(self.index.index_doc).with_args(1, self),
					 raises(TypeError))

	def test_index_sort(self):
		index = self.index
		self.field = 1
		index.index_doc( 1, self )
		self.field = 2
		index.index_doc( 2, self )
		self.field = 3
		index.index_doc( 3, self )

		assert_that( index.sort((1,2,3), reverse=True),
					 contains(3, 2, 1))

		assert_that( index.sort((3, 2, 1), reverse=False),
					 contains(1, 2, 3))
