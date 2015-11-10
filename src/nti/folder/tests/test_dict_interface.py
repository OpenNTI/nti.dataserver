#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
does_not = is_not

import unittest

from Acquisition import aq_base

from nti.folder.ordered import OrderedBTreeFolderBase

from nti.folder.tests import DummyObject
from nti.folder.tests import SharedConfiguringTestLayer

class TestDictInterface(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_getitem(self):
		folder = OrderedBTreeFolderBase("f1")
		foo = DummyObject('foo')
		folder._setOb('foo', foo)
		assert_that(folder['foo'], is_(foo))
		assert_that(folder.__getitem__('foo'), is_(foo))
		self.assertRaises(KeyError, folder.__getitem__, 'bar')

	def test_setitem(self):
		folder = OrderedBTreeFolderBase("f1")
		foo = DummyObject('foo')
		folder['foo'] = foo
		assert_that(folder._getOb('foo'), is_(foo))

	def test_contains(self):
		folder = OrderedBTreeFolderBase("f1")
		folder._setOb('foo', DummyObject('foo'))
		folder._setOb('bar', DummyObject('bar'))
		assert_that('foo', is_in(folder))
		assert_that('bar', is_in(folder))

	def test_delitem(self):
		folder = OrderedBTreeFolderBase("f1")
		folder._setOb('foo', DummyObject('foo'))
		folder._setOb('bar', DummyObject('bar'))
		assert_that(folder.objectIds(), has_length(2))
		del folder['foo']
		del folder['bar']
		assert_that(folder.objectIds(), has_length(0))

	def test_len_empty_folder(self):
		folder = OrderedBTreeFolderBase("f1")
		assert_that(folder, has_length(0))

	def test_len_one_child(self):
		folder = OrderedBTreeFolderBase("f1")
		folder['child'] = DummyObject('child')
		assert_that(folder, has_length(1))

	def test_to_verify_ticket_9120(self):
		folder = OrderedBTreeFolderBase("f1")
		folder['ob1'] = ob1 = DummyObject('ob1')
		folder['ob2'] = DummyObject('ob2')
		folder['ob3'] = DummyObject('ob3')
		folder['ob4'] = ob4 = DummyObject('ob4')
		del folder['ob2']
		del folder['ob3']
		assert_that(folder.keys(), is_(['ob1', 'ob4']))
		assert_that(map(aq_base, folder.values()), is_([ob1, ob4]))
		assert_that([key in folder for key in folder], is_([True, True]))

class RelatedToDictInterfaceTests(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def create(self):
		folder = OrderedBTreeFolderBase("f1")
		folder._setOb('o1', DummyObject('o1'))
		folder._setOb('o2', DummyObject('o2'))
		folder._setOb('o3', DummyObject('o3'))
		folder._setOb('o4', DummyObject('o4'))
		return folder

	def testObjectIdsWithSpec(self):
		folder = self.create()
		assert_that(folder.objectIds(), is_([u'o1', u'o2', u'o3', u'o4']))
		folder.moveObjectsToTop(['o3'])
		folder.moveObjectsDown(['o2'])
		assert_that(folder.objectIds(), is_([u'o3', u'o1', u'o4', u'o2']))
