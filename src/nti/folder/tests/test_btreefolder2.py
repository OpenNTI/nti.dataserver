#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import not_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import same_instance
does_not = is_not

import unittest

from Acquisition import aq_base

from nti.folder.ofs.folder import Folder

from nti.folder.btreefolder2 import BTreeFolder2
from nti.folder.btreefolder2 import ExhaustedUniqueIdsError

from nti.folder.tests import SharedConfiguringTestLayer

class TrojanKey:
	"""
	Pretends to be a consistent, immutable, humble citizen...

	then sweeps the rug out from under the BTree.
	"""
	def __init__(self, value):
		self.value = value

	def __cmp__(self, other):
		return cmp(self.value, other)

	def __hash__(self):
		return hash(self.value)

class TestBTreeFolder2(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def getBase(self, ob):
		# This is overridden in subclasses.
		return aq_base(ob)

	def setUp(self):
		self.f = BTreeFolder2('root')
		ff = BTreeFolder2('item')
		self.f._setOb(ff.id, ff)
		self.ff = self.f._getOb(ff.id)

	def test_Added(self):
		self.assertEqual(self.ff.id, 'item')

	def test_SetItem(self):
		self.f['ff2'] = BTreeFolder2('item2')
		assert_that(self.f.ff2.id, is_('item2'))

	def test__getattr_found(self):
		assert_that(getattr(self.f, 'item'), is_(self.ff))

	def test__getattr_notfound(self):
		self.assertRaises(AttributeError, getattr, self.f, 'none')

	def test__getattr_default(self):
		assert_that(getattr(self.f, 'none', '1'), is_('1'))

	def test_count(self):
		assert_that(self.f.objectCount(), is_(1))
		assert_that(self.ff.objectCount(), is_(0))

	def test_len(self):
		assert_that(self.f, has_length(1))
		assert_that(self.ff, has_length(0))

	def test_non_zero(self):
		assert_that(bool(self.f), is_(True))
		assert_that(bool(self.ff), is_(True))

	def test_objectIds(self):
		assert_that(list(self.f.objectIds()), is_(['item']))
		assert_that(list(self.ff.objectIds()), is_([]))
		f3 = BTreeFolder2('item3')
		self.f._setOb(f3.id, f3)
		lst = list(self.f.objectIds())
		lst.sort()
		assert_that(lst, is_(['item', 'item3']))

	def test_keys(self):
		assert_that(list(self.f.keys()), is_(['item']))
		assert_that(list(self.ff.keys()), is_([]))
		f3 = BTreeFolder2('item3')
		self.f[f3.id] = f3
		lst = list(self.f.keys())
		lst.sort()
		assert_that(lst, is_(['item', 'item3']))

	def test_objectValues(self):
		values = self.f.objectValues()
		assert_that(values, has_length(1))
		assert_that(values[0], has_property('id', is_('item')))
		assert_that(values[0], has_property('aq_parent', is_(self.f)))

	def test_values(self):
		values = self.f.values()
		assert_that(values, has_length(1))
		assert_that(values[0].id, is_('item'))

	def test_objectItems(self):
		items = self.f.objectItems()
		assert_that(items, has_length(1))
		uid, val = items[0]
		assert_that(uid, is_('item'))
		assert_that(val, has_property('id', 'item'))
		assert_that(val, has_property('aq_parent', is_(self.f)))

	def test_items(self):
		items = self.f.items()
		self.assertEqual(len(items), 1)
		uid, val = items[0]
		assert_that(uid, is_('item'))
		assert_that(val, has_property('id', 'item'))

	def test_has_key(self):
		assert_that(self.f.hasObject('item'), is_(True))  # Old spelling
		assert_that(self.f.has_key('item'), is_(True))  # New spelling

	def test_contains(self):
		assert_that('item', is_in(self.f))

	def test_delete(self):
		self.f._delOb('item')
		assert_that(list(self.f.objectIds()), is_([]))
		assert_that(self.f.objectCount(), is_(0))

	def test_delitem(self):
		del self.f['item']
		assert_that('item', not_(is_in(self.f)))
		assert_that(self.f, has_length(0))

	def test_iter(self):
		iterator = iter(self.f)
		first = iterator.next()
		assert_that(first, is_('item'))
		self.assertRaises(StopIteration, iterator.next)

	def test__checkId(self):
		assert_that(self.f._checkId('xyz'), is_(none()))

	def test__setObject(self):
		f2 = BTreeFolder2('item2')
		self.f._setObject(f2.id, f2)
		assert_that('item2', is_in(self.f))
		assert_that(self.f.objectCount(), is_(2))

	def test_wrapped(self):
		# Verify that the folder returns wrapped versions of objects.
		base = self.getBase(self.f._getOb('item'))
		assert_that(self.f._getOb('item'), is_not(same_instance(base)))
		assert_that(self.f['item'], is_not(same_instance(base)))
		assert_that(self.f.get('item'), is_not(same_instance(base)))
		assert_that(self.getBase(self.f._getOb('item')), is_(base))

	def test_generateId(self):
		ids = {}
		for _ in range(10):
			ids[self.f.generateId()] = 1
		assert_that(ids, has_length(10))  # All unique
		for uid in ids.keys():
			self.f._checkId(uid)  # Must all be valid

	def test_generateId_denialOfService_prevention(self):
		for n in range(10):
			item = Folder()
			item.id = 'item%d' % n
			self.f._setOb(item.id, item)
		self.f.generateId('item', rand_ceiling=20)  # Shouldn't be a problem
		self.assertRaises(ExhaustedUniqueIdsError,
						  self.f.generateId, 'item', rand_ceiling=9)

	def test_Replace(self):
		old_f = Folder()
		old_f.id = 'item'
		inner_f = BTreeFolder2('inner')
		old_f._setObject(inner_f.id, inner_f)
		self.ff._populateFromFolder(old_f)
		assert_that(self.ff.objectCount(), is_(1))
		assert_that('inner', is_in(self.ff))
		assert_that(self.getBase(self.ff._getOb('inner')), is_(inner_f))

	def test_cleanup(self):
		self.assert_(self.f._cleanup())
		key = TrojanKey('a')
		self.f._tree[key] = 'b'
		self.assert_(self.f._cleanup())
		key.value = 'z'

		# With a key in the wrong place, there should now be damage.
		self.assert_(not self.f._cleanup())

		# Now it's fixed.
		self.assert_(self.f._cleanup())
