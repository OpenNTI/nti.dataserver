#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""

from __future__ import print_function, unicode_literals

from nti.externalization.persistence import PersistentExternalizableList, PersistentExternalizableWeakList

import unittest
from persistent import Persistent
from nose.tools import assert_raises

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not

class TestPersistentExternalizableList(unittest.TestCase):

	def test_externalize(self):
		obj = PersistentExternalizableList([1,2, None, 3])

		assert_that( obj.toExternalList(), is_( [1,2,3] ) )
		assert_that( obj.toExternalList(), is_( list ) )

	def test_values(self):
		obj = PersistentExternalizableList([1,2, None, 3])

		assert_that( obj.values(), is_( obj ) )
		assert_that( list( iter(obj.values() ) ), is_( [1,2,None,3] ) )


class TestPersistentExternalizableWeakList(unittest.TestCase):

	def test_mutate(self):

		obj = PersistentExternalizableWeakList()

		# Cannot set non-persistent objects
		with assert_raises( AttributeError ):
			obj.append( object() )

		pers = Persistent()
		obj.append( pers )
		assert_that( obj[0], is_( pers ) )

		pers2 = Persistent()
		obj[0] = pers2
		assert_that( obj[0], is_( pers2 ) )
		assert_that( obj.count( pers2 ), is_( 1 ) )
		assert_that( obj.count( pers ), is_( 0 ) )

		# iteration
		for x in obj:
			assert_that( x, is_( pers2 ) )
		assert_that( obj.index( pers2 ), is_( 0 ) )

		assert_that( obj.pop(), is_( pers2 ) )
		with assert_raises( IndexError ):
			obj.pop()

		assert_that( obj, is_( obj ) )

		obj.append( pers2 )
		# mul
		assert_that( obj * 2, is_( PersistentExternalizableWeakList( [pers2, pers2] ) ) )

		# imul
		obj *= 2
		assert_that( obj, is_( PersistentExternalizableWeakList( [pers2, pers2] ) ) )

		obj.pop()
		# insert
		obj.insert( 1, pers2 )
		assert_that( obj, is_( PersistentExternalizableWeakList( [pers2, pers2] ) ) )

		assert_that( obj, is_( [pers2, pers2] ) )
		assert_that( obj, is_not( [pers2, pers] ) )
		assert_that( obj, is_not( pers ) )
