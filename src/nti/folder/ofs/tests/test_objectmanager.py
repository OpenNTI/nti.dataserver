#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import not_
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import same_instance
does_not = is_not

import unittest

from Acquisition import Implicit

from zope.container.interfaces import IContainer

from zope.interface import implementer
from zope.interface.verify import verifyClass

from nti.folder.ofs.interfaces import IItem
from nti.folder.ofs.interfaces import IObjectManager

from nti.folder.ofs.item import SimpleItem

from nti.folder.ofs.objectmanager import ObjectManager

from nti.folder.tests import SharedConfiguringTestLayer

class FauxRoot(Implicit):

	id = '/'

	def getPhysicalRoot(self):
		return self

	def getPhysicalPath(self):
		return ()

class FauxUser(Implicit):

	def __init__(self, uid, login):
		self._id = uid
		self._login = login

	def getId(self):
		return self._id

@implementer(IItem)
class ObjectManagerWithIItem(ObjectManager):
	pass

class TestObjectManager(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def _getTargetClass(self):
		return ObjectManagerWithIItem

	def _makeOne(self, *args, **kw):
		return self._getTargetClass()(*args, **kw).__of__(FauxRoot())

	def test_interfaces(self):
		verifyClass(IContainer, ObjectManager)
		verifyClass(IObjectManager, ObjectManager)

	def test_hasObject(self):
		om = self._makeOne()
		assert_that(om.hasObject('_properties'), is_(False))
		assert_that(om.hasObject('_getOb'), is_(False))
		assert_that(om.hasObject('__of__'), is_(False))
		assert_that(om.hasObject('.'), is_(False))
		assert_that(om.hasObject('..'), is_(False))
		assert_that(om.hasObject('aq_base'), is_(False))
		om.zap__ = True
		assert_that(om.hasObject('zap__'), is_(False))
		assert_that(om.hasObject('foo'), is_(False))
		si = SimpleItem('foo')
		om._setObject('foo', si)
		assert_that(om.hasObject('foo'), is_(True))
		om._delObject('foo')
		assert_that(om.hasObject('foo'), is_(False))
		om['foo'] = si
		assert_that(om.hasObject('foo'), is_(True))

	def test_setObject_checkId_ok(self):
		om = self._makeOne()
		si = SimpleItem('1')
		om._setObject('AB-dash_under0123', si)
		si = SimpleItem('2')
		om._setObject('ho.bak~', si)
		si = SimpleItem('3')
		om._setObject('dot.comma,dollar$(hi)hash# space', si)
		si = SimpleItem('4')
		om._setObject('b@r', si)
		si = SimpleItem('5')
		om._setObject('..haha', si)
		si = SimpleItem('6')
		om._setObject('.bashrc', si)

	def test_setObject_checkId_bad(self):
		om = self._makeOne()
		si = SimpleItem('111')
		om._setObject('111', si)
		si = SimpleItem('2')
		self.assertRaises(ValueError, om._setObject, 123, si)
		self.assertRaises(ValueError, om._setObject, 'a\x01b', si)
		self.assertRaises(ValueError, om._setObject, 'a\\b', si)
		self.assertRaises(ValueError, om._setObject, 'a:b', si)
		self.assertRaises(ValueError, om._setObject, 'a;b', si)
		self.assertRaises(ValueError, om._setObject, '.', si)
		self.assertRaises(ValueError, om._setObject, '..', si)
		self.assertRaises(ValueError, om._setObject, '_foo', si)
		self.assertRaises(ValueError, om._setObject, 'aq_me', si)
		self.assertRaises(ValueError, om._setObject, 'bah__', si)
		self.assertRaises(ValueError, om._setObject, '111', si)
		self.assertRaises(ValueError, om._setObject, '/', si)
		self.assertRaises(ValueError, om._setObject, 'get', si)
		self.assertRaises(ValueError, om._setObject, 'items', si)
		self.assertRaises(ValueError, om._setObject, 'keys', si)
		self.assertRaises(ValueError, om._setObject, 'values', si)

	def test_getsetitem(self):
		om = self._makeOne()
		si1 = SimpleItem('1')
		si2 = SimpleItem('2')
		om['1'] = si1
		self.assertTrue('1' in om)
		self.assertTrue(si1 in om.objectValues())
		self.assertTrue('1' in om.objectIds())
		om['2'] = si2
		assert_that('2', is_in(om))
		assert_that(si2, is_in(om.objectValues()))
		assert_that('2', is_in(om.objectIds()))
		self.assertRaises(ValueError, om._setObject, '1', si2)
		self.assertRaises(ValueError, om.__setitem__, '1', si2)

	def test_delitem(self):
		om = self._makeOne()
		si1 = SimpleItem('1')
		si2 = SimpleItem('2')
		om['1'] = si1
		om['2'] = si2
		assert_that('1', is_in(om))
		assert_that('2', is_in(om))
		del om['1']
		assert_that('1', not_(is_in(om)))
		assert_that('2', is_in(om))
		om._delObject('2')
		assert_that('2', not_(is_in(om)))

	def test_iterator(self):
		om = self._makeOne()
		si1 = SimpleItem('1')
		si2 = SimpleItem('2')
		om['1'] = si1
		om['2'] = si2
		iterator = iter(om)
		assert_that(hasattr(iterator, '__iter__'), is_(True))
		assert_that(hasattr(iterator, 'next'), is_(True))
		result = [i for i in iterator]
		assert_that('1', is_in(result))
		assert_that('2', is_in(result))

	def test_len(self):
		om = self._makeOne()
		si1 = SimpleItem('1')
		si2 = SimpleItem('2')
		om['1'] = si1
		om['2'] = si2
		assert_that(om, has_length(2))

	def test_nonzero(self):
		om = self._makeOne()
		assert_that(bool(om), is_(True))

	def test___getitem___miss(self):
		om = self._makeOne()
		self.assertRaises(KeyError, om.__getitem__, 'nonesuch')

	def test___getitem___miss_w_non_instance_attr(self):
		om = self._makeOne()
		self.assertRaises(KeyError, om.__getitem__, 'get')

	def test___getitem___hit(self):
		om = self._makeOne()
		si1 = SimpleItem('1')
		om['1'] = si1
		got = om['1']
		assert_that(got.aq_self, is_(same_instance(si1)))
		assert_that(got.aq_parent, is_(same_instance(om)))
		assert_that(got, has_property('__parent__', is_(same_instance(om))))
		
	def test_get_hit(self):
		om = self._makeOne()
		si1 = SimpleItem('1')
		om['1'] = si1
		got = om.get('1')
		assert_that(got.aq_self, is_(same_instance(si1)))
		assert_that(got, has_property('aq_parent', is_(same_instance(om))))

	def test_items(self):
		om = self._makeOne()
		si1 = SimpleItem('1')
		om['1'] = si1
		assert_that(('1', si1), is_in(om.items()))

	def test_keys(self):
		om = self._makeOne()
		si1 = SimpleItem('1')
		om['1'] = si1
		assert_that('1', is_in(om.keys()))

	def test_values(self):
		om = self._makeOne()
		si1 = SimpleItem('1')
		om['1'] = si1
		assert_that(si1, is_in(om.values()))
