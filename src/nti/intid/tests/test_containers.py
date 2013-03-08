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
from ..containers import IntidContainedStorage

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

class TestIntidContainedStorage(nti.tests.AbstractTestBase):

	class MockUtility(object):

		data = None

		def getObject( self, key ):
			return self.data[key]

		def getId( self, obj ):
			for k, v in self.data.items():
				if obj == v:
					return k
			raise KeyError()

	class FixedUtilityIntidContainedStorage(IntidContainedStorage):
		utility = None
		def _get_intid_for_object_from_utility(self, contained):
			return self.utility.getId( contained )

	def setUp(self):
		super(TestIntidContainedStorage,self).setUp()
		self.utility = self.MockUtility()
		self.utility.data = {i: object() for i in range(10)}
		self.storage = self.FixedUtilityIntidContainedStorage()
		self.storage.utility = self.utility

	def test_len(self):
		storage = self.storage
		containers = self.storage # the facade stays in sync

		def assert_len( i ):
			assert_that( storage, has_length( i ) )
			assert_that( containers, has_length( i ) )

		assert_len( 0 )
		storage.addContainedObjectToContainer( self.utility.data[1] )
		assert_len( 1 )
		storage.addContainedObjectToContainer( self.utility.data[2], 'b' )
		assert_len( 2 )

		# As it is the length of the containers, removing from a container doesn't
		# change anything
		storage.deleteEqualContainedObjectFromContainer( self.utility.data[1] )
		assert_len( 2 )

		storage.deleteEqualContainedObjectFromContainer( self.utility.data[2], 'b' )
		assert_len( 2 )

		storage.popContainer( '' )
		assert_len( 1 )

		storage.popContainer( 'b' )
		assert_len( 0 )
