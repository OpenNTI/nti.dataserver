#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that
does_not = is_not

import unittest

from nti.folder.interfaces import IOrdering
from nti.folder.ordered import OrderedBTreeFolderBase

from nti.folder.tests import DummyObject
from nti.folder.tests import SharedConfiguringTestLayer

class TestsOFSOrderSupport(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def create(self):
		folder = OrderedBTreeFolderBase('f1')
		folder['o1'] = DummyObject('o1', 'mt1')
		folder['o2'] = DummyObject('o2', 'mt2')
		folder['o3'] = DummyObject('o3', 'mt1')
		folder['o4'] = DummyObject('o4', 'mt2')
		return folder

	def test_objectIds_ordered(self):
		folder = self.create()
		assert_that(folder.objectIds(), is_(["o1", "o2", "o3", "o4"]))
		folder.moveObjectsUp(("o2",), 1)
		assert_that(folder.objectIds(), is_(["o2", "o1", "o3", "o4"]))

	def test_objectValues_ordered(self):
		folder = self.create()
		assert_that(
			[x.id for x in folder.objectValues()],
			is_(["o1", "o2", "o3", "o4"]),
		)
		folder.moveObjectsUp(("o2",), 1)
		assert_that(
			[x.id for x in folder.objectValues()],
			is_(["o2", "o1", "o3", "o4"])
		)

	def test_objectItemsOrdered(self):
		folder = self.create()
		assert_that(
			[x for x, _ in folder.objectItems()],
			is_(["o1", "o2", "o3", "o4"])
		)
		folder.moveObjectsUp(("o2",), 1)
		assert_that(
			[x for x, _ in folder.objectItems()],
			is_(["o2", "o1", "o3", "o4"])
		)

	def test_iterkeys(self):
		folder = self.create()
		assert_that(
			[x for x in folder.iterkeys()],
			is_(["o1", "o2", "o3", "o4"])

		)
		folder.moveObjectsUp(("o2",), 1)
		assert_that(
			[x for x in folder.iterkeys()],
			is_(["o2", "o1", "o3", "o4"])
		)

	def test_iter(self):
		folder = self.create()
		assert_that([x for x in folder], is_(["o1", "o2", "o3", "o4"]))
		folder.moveObjectsUp(("o2",), 1)
		assert_that([x for x in folder], is_(["o2", "o1", "o3", "o4"]))

	def test_getitem(self):
		ordering = IOrdering(self.create())
		assert_that(ordering[1], is_('o2'))
		assert_that(ordering[-1], is_('o4'))
		assert_that(ordering[1:2], is_(['o2']))
		assert_that(ordering[1:-1], is_(['o2', 'o3']))
		assert_that(ordering[1:], is_(['o2', 'o3', 'o4']))

	def runTableTests(self, methodname, table):
		for args, order, rval in table:
			f = self.create()
			method = getattr(f, methodname)
			if rval == 'ValueError':
				self.failUnlessRaises(ValueError, method, *args)
			else:
				self.failUnlessEqual(method(*args), rval)
			self.failUnlessEqual(f.objectIds(), order)

	def test_moveObjectsUp(self):
		self.runTableTests('moveObjectsUp',
			  ((('o4', 1), ['o1', 'o2', 'o4', 'o3'], 1)
			  , (('o4', 2), ['o1', 'o4', 'o2', 'o3'], 1)
			  , ((('o1', 'o3'), 1), ['o1', 'o3', 'o2', 'o4'], 1)
			  , ((('o1', 'o3'), 9), ['o1', 'o3', 'o2', 'o4'], 1)
			  , ((('o2', 'o3'), 1), ['o2', 'o3', 'o1', 'o4'], 2)
			  , ((('o2', 'o3'), 1, ('o1', 'o2', 'o3', 'o4')),
									   ['o2', 'o3', 'o1', 'o4'], 2)
			  , ((('o2', 'o3'), 1, ('o2', 'o3', 'o4')),
									   ['o1', 'o2', 'o3', 'o4'], 0)
			  , ((('n2', 'o3'), 1), ['o1', 'o3', 'o2', 'o4'], 1)
			  , ((('o3', 'o1'), 1), ['o1', 'o3', 'o2', 'o4'], 1)
			  )
			)

	def test_moveObjectsDown(self):
		self.runTableTests('moveObjectsDown',
			  ((('o1', 1), ['o2', 'o1', 'o3', 'o4'], 1)
			  , (('o1', 2), ['o2', 'o3', 'o1', 'o4'], 1)
			  , ((('o2', 'o4'), 1), ['o1', 'o3', 'o2', 'o4'], 1)
			  , ((('o2', 'o4'), 9), ['o1', 'o3', 'o2', 'o4'], 1)
			  , ((('o2', 'o3'), 1), ['o1', 'o4', 'o2', 'o3'], 2)
			  , ((('o2', 'o3'), 1, ('o1', 'o2', 'o3', 'o4')),
									   ['o1', 'o4', 'o2', 'o3'], 2)
			  , ((('o2', 'o3'), 1, ('o1', 'o2', 'o3')),
									   ['o1', 'o2', 'o3', 'o4'], 0)
			  , ((('n2', 'o3'), 1), ['o1', 'o2', 'o4', 'o3'], 1)
			  , ((('o4', 'o2'), 1), ['o1', 'o3', 'o2', 'o4'], 1)
			  )
			)

	def test_moveObjectsToTop(self):
		self.runTableTests('moveObjectsToTop',
			  ((('o4',), ['o4', 'o1', 'o2', 'o3'], 1)
			  , ((('o1', 'o3'),), ['o1', 'o3', 'o2', 'o4'], 1)
			  , ((('o2', 'o3'),), ['o2', 'o3', 'o1', 'o4'], 2)
			  , ((('o2', 'o3'), ('o1', 'o2', 'o3', 'o4')),
									 ['o2', 'o3', 'o1', 'o4'], 2)
			  , ((('o2', 'o3'), ('o2', 'o3', 'o4')),
									 ['o1', 'o2', 'o3', 'o4'], 0)
			  , ((('n2', 'o3'),), ['o3', 'o1', 'o2', 'o4'], 1)
			  , ((('o3', 'o1'),), ['o3', 'o1', 'o2', 'o4'], 1)
			  )
			)

	def test_moveObjectsToBottom(self):
		self.runTableTests('moveObjectsToBottom',
			  ((('o1',), ['o2', 'o3', 'o4', 'o1'], 1)
			  , ((('o2', 'o4'),), ['o1', 'o3', 'o2', 'o4'], 1)
			  , ((('o2', 'o3'),), ['o1', 'o4', 'o2', 'o3'], 2)
			  , ((('o2', 'o3'), ('o1', 'o2', 'o3', 'o4')),
									 ['o1', 'o4', 'o2', 'o3'], 2)
			  , ((('o2', 'o3'), ('o1', 'o2', 'o3')),
									 ['o1', 'o2', 'o3', 'o4'], 0)
			  , ((('n2', 'o3'),), ['o1', 'o2', 'o4', 'o3'], 1)
			  , ((('o4', 'o2'),), ['o1', 'o3', 'o4', 'o2'], 1)
			  )
			)

	def test_orderObjects(self):
		self.runTableTests('orderObjects',
			  ((('id', 'id'), 	   ['o4', 'o3', 'o2', 'o1'], -1)
			  , (('meta_type', ''), ['o1', 'o3', 'o2', 'o4'], -1)
			  # for the next line the sort order is different from the
			  # original test in OFS, since the current implementation
			  # keeps the original order as much as possible, i.e. minimize
			  # exchange operations within the list;  this is correct as
			  # far as the test goes, since it didn't specify a secondary
			  # sort key...
			  , (('meta_type', 'n'), ['o2', 'o4', 'o1', 'o3'], -1)
			  )
			)

	def test_getObjectPosition(self):
		self.runTableTests('getObjectPosition',
			  ((('o2',), ['o1', 'o2', 'o3', 'o4'], 1)
			  , (('o4',), ['o1', 'o2', 'o3', 'o4'], 3)
			  , (('n2',), ['o1', 'o2', 'o3', 'o4'], 'ValueError')
			  )
			)

	def test_moveObjectToPosition(self):
		self.runTableTests('moveObjectToPosition',
			  ((('o2', 2), ['o1', 'o3', 'o2', 'o4'], 1)
			  , (('o4', 2), ['o1', 'o2', 'o4', 'o3'], 1)
			  , (('n2', 2), ['o1', 'o2', 'o3', 'o4'], 'ValueError')
			  )
			)

class TestsPloneOrderSupport(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def setUp(self):
		self.folder = OrderedBTreeFolderBase("f1")
		self.folder['foo'] = DummyObject('foo', 'mt1')
		self.folder['bar'] = DummyObject('bar', 'mt1')
		self.folder['baz'] = DummyObject('baz', 'mt1')

	def test_getObjectPosition(self):
		assert_that(self.folder.getObjectPosition('foo'), is_(0))
		assert_that(self.folder.getObjectPosition('bar'), is_(1))
		assert_that(self.folder.getObjectPosition('baz'), is_(2))

	def test_moveObject(self):
		self.folder.moveObjectToPosition('foo', 1)
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('foo'), is_(1))
		assert_that(self.folder.getObjectPosition('baz'), is_(2))

	def test_moveObjectToSamePos(self):
		self.folder.moveObjectToPosition('bar', 1)
		assert_that(self.folder.getObjectPosition('foo'), is_(0))
		assert_that(self.folder.getObjectPosition('bar'), is_(1))
		assert_that(self.folder.getObjectPosition('baz'), is_(2))

	def test_moveObjectToFirstPos(self):
		self.folder.moveObjectToPosition('bar', 0)
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('foo'), is_(1))
		assert_that(self.folder.getObjectPosition('baz'), is_(2))

	def test_moveObjectToLastPos(self):
		self.folder.moveObjectToPosition('bar', 2)
		assert_that(self.folder.getObjectPosition('foo'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), is_(1))
		assert_that(self.folder.getObjectPosition('bar'), is_(2))

	def test_moveObjectOutLowerBounds(self):
		# Pos will be normalized to 0
		self.folder.moveObjectToPosition('bar', -1)
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('foo'), is_(1))
		assert_that(self.folder.getObjectPosition('baz'), is_(2))

	def test_moveObjectOutUpperBounds(self):
		# Pos will be normalized to 2
		self.folder.moveObjectToPosition('bar', 3)
		assert_that(self.folder.getObjectPosition('foo'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), is_(1))
		assert_that(self.folder.getObjectPosition('bar'), is_(2))

	def test_moveObjectsUp(self):
		self.folder.moveObjectsUp(['bar'])
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('foo'), is_(1))
		assert_that(self.folder.getObjectPosition('baz'), is_(2))

	def test_moveObjectsDown(self):
		self.folder.moveObjectsDown(['bar'])
		assert_that(self.folder.getObjectPosition('foo'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), 1)
		assert_that(self.folder.getObjectPosition('bar'), is_(2))

	def test_moveObjectsToTop(self):
		self.folder.moveObjectsToTop(['bar'])
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('foo'), is_(1))
		assert_that(self.folder.getObjectPosition('baz'), is_(2))

	def test_moveObjectsToBottom(self):
		self.folder.moveObjectsToBottom(['bar'])
		assert_that(self.folder.getObjectPosition('foo'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), is_(1))
		assert_that(self.folder.getObjectPosition('bar'), is_(2))

	def test_moveTwoObjectsUp(self):
		self.folder.moveObjectsUp(['bar', 'baz'])
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), is_(1))
		assert_that(self.folder.getObjectPosition('foo'), is_(2))

	def test_moveTwoObjectsDown(self):
		self.folder.moveObjectsDown(['foo', 'bar'])
		assert_that(self.folder.getObjectPosition('baz'), is_(0))
		assert_that(self.folder.getObjectPosition('foo'), is_(1))
		assert_that(self.folder.getObjectPosition('bar'), is_(2))

	def test_moveTwoObjectsToTop(self):
		self.folder.moveObjectsToTop(['bar', 'baz'])
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), is_(1))
		assert_that(self.folder.getObjectPosition('foo'), is_(2))

	def test_moveTwoObjectsToBottom(self):
		self.folder.moveObjectsToBottom(['foo', 'bar'])
		assert_that(self.folder.getObjectPosition('baz'), is_(0))
		assert_that(self.folder.getObjectPosition('foo'), is_(1))
		assert_that(self.folder.getObjectPosition('bar'), is_(2))

	def test_orderObjects(self):
		self.folder.orderObjects('id')
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), is_(1))
		assert_that(self.folder.getObjectPosition('foo'), is_(2))

	def test_orderObjectsReverse(self):
		self.folder.orderObjects('id', reverse=True)
		assert_that(self.folder.getObjectPosition('foo'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), is_(1))
		assert_that(self.folder.getObjectPosition('bar'), is_(2))

	def test_orderObjectsByMethod(self):
		self.folder.orderObjects('dummy_method')
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), is_(1))
		assert_that(self.folder.getObjectPosition('foo'), is_(2))

	def test_orderObjectsOnlyReverse(self):
		self.folder.orderObjects(reverse=True)
		assert_that(self.folder.getObjectPosition('baz'), is_(0))
		assert_that(self.folder.getObjectPosition('bar'), is_(1))
		assert_that(self.folder.getObjectPosition('foo'), is_(2))

	def test_subsetIds(self):
		self.folder.moveObjectsByDelta(['baz'], -1, ['foo', 'bar', 'baz'])
		assert_that(self.folder.getObjectPosition('foo'), is_(0))
		assert_that(self.folder.getObjectPosition('baz'), is_(1))
		assert_that(self.folder.getObjectPosition('bar'), is_(2))

	def test_skipObjectsNotInSubsetIds(self):
		self.folder.moveObjectsByDelta(['baz'], -1, ['foo', 'baz'])
		assert_that(self.folder.getObjectPosition('baz'), is_(0))
		assert_that(self.folder.getObjectPosition('bar'), is_(1))  # no move
		assert_that(self.folder.getObjectPosition('foo'), is_(2))

	def test_ignoreNonObjects(self):
		self.folder.moveObjectsByDelta(['bar', 'blah'], -1)
		assert_that(self.folder.getObjectPosition('bar'), is_(0))
		assert_that(self.folder.getObjectPosition('foo'), is_(1))
		assert_that(self.folder.getObjectPosition('baz'), is_(2))
