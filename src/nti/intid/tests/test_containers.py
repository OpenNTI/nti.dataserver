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
from hamcrest import is_in
from hamcrest import is_not
does_not = is_not
from hamcrest import has_key
from hamcrest import has_length

import nti.tests

import BTrees

from ..containers import IntidResolvingMappingFacade

class TestMappingFacade(nti.tests.AbstractTestBase):

	class MockUtility(object):

		data = None

		def getObject( self, key ):
			return self.data[key]

	def setUp(self):
		super(TestMappingFacade,self).setUp()
		self.utility = self.MockUtility()
		self.utility.data = {i: object() for i in range(10)}

		btree = BTrees.family64.OO.BTree()
		btree['a'] = BTrees.family64.II.TreeSet()
		btree['a'].add( 1 )
		btree['a'].add( 2 )
		btree['a'].add( 3 )
		btree['b'] = BTrees.family64.II.TreeSet()
		btree['b'].add( 4 )
		self.btree = btree

		self.facade = IntidResolvingMappingFacade( btree, intids=self.utility )

	def test_keys(self):
		assert_that( list(self.facade), is_( ['a','b'] ) )
		assert_that( list(self.facade.keys()), is_( ['a','b'] ) )

		assert_that( self.facade, has_key( 'a' ) )
		assert_that( self.facade, does_not( has_key( 'c' ) ) )

		assert_that( self.facade, has_length( 2 ) )

	def test_get(self):
		facade = self.facade
		# iter unpack
		[obj] = facade['b']
		assert_that( obj, is_( self.utility.data[4] ) )

		[obj] = list(facade.values())[1]
		assert_that( obj, is_( self.utility.data[4] ) )

		assert_that( self.utility.data[4], is_in( facade['b'] ) )
