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
