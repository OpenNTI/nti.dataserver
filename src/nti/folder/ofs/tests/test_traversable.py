#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import assert_that
does_not = is_not

import unittest
from operator import getitem

from Acquisition import aq_base
from Acquisition import Implicit

from zope.event import notify

from zope.interface.verify import verifyClass

from zope.lifecycleevent import ObjectCreatedEvent

from persistent import Persistent

from nti.folder.ofs.folder import Root
from nti.folder.ofs.folder import Folder
from nti.folder.ofs.item import SimpleItem
from nti.folder.ofs.item import ItemWithName

from nti.folder.ofs.interfaces import ITraversable

from nti.folder.ofs.traversable import NotFound
from nti.folder.ofs.traversable import Traversable

from nti.folder.tests import SharedConfiguringTestLayer

def manage_addFolder(self, uid, title=''):
	ob = Folder(uid)
	ob.title = title
	self._setObject(uid, ob)
	ob = self._getOb(uid)
	return ob

class File(Persistent, Implicit, ItemWithName):

	def __init__(self, uid, title, content_type=''):
		self.__name__ = uid
		self.title = title
		self.content_type = content_type

	def id(self):
		return self.__name__

def manage_addFile(self, uid, title='', content_type=''):
	uid = str(uid)
	title = str(title)
	content_type = str(content_type)

	self._setObject(uid, File(uid, title, content_type))
	newFile = self._getOb(uid)

	notify(ObjectCreatedEvent(newFile))
	return newFile

class TestTraversable(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def setUp(self):
		self.app = Root()
		manage_addFolder(self.app, 'folder1')
		folder1 = getattr(self.app, 'folder1')
		setattr(folder1, '+something', 'plus')

		self.folder1 = getattr(self.app, 'folder1')
		setattr(self.folder1, '+something', 'plus')

		manage_addFile(self.folder1, 'file', content_type='text/plain')
		self.folder1 = getattr(self.app, 'folder1')

	def test_interfaces(self):
		verifyClass(ITraversable, Traversable)

	def test_traversePath(self):
		assert_that('file', is_in(self.folder1.objectIds()))
		assert_that(
			self.folder1.unrestrictedTraverse(('', 'folder1', 'file')), is_not(none()))
		assert_that(
			self.folder1.unrestrictedTraverse(('', 'folder1')), is_not(none()))

	def test_traverseURLNoSlash(self):
		assert_that('file', is_in(self.folder1.objectIds()))
		assert_that(self.folder1.unrestrictedTraverse('/folder1/file'), is_not(none()))
		assert_that(self.folder1.unrestrictedTraverse('/folder1'), is_not(none()))

	def test_traverseURLSlash(self):
		assert_that('file', is_in(self.folder1.objectIds()))
		assert_that(self.folder1.unrestrictedTraverse('/folder1/file/'), is_not(none()))
		assert_that(self.folder1.unrestrictedTraverse('/folder1/') , is_not(none()))

	def test_traverseToNone(self):
		self.assertRaises(
			KeyError,
			self.folder1.unrestrictedTraverse, ('', 'folder1', 'file2'))
		self.assertRaises(
			KeyError, self.folder1.unrestrictedTraverse, '/folder1/file2')
		self.assertRaises(
			KeyError, self.folder1.unrestrictedTraverse, '/folder1/file2/')

	def test_traverseUp(self):
		# Test that we can traverse upwards
		assert_that(
			aq_base(self.app.folder1.file.restrictedTraverse('../..')),
			is_(aq_base(self.app)))
	
	def test_notFoundIsRaised(self):
		self.folder1._setObject('foo', SimpleItem('foo'))
		self.assertRaises(AttributeError, getitem, self.folder1.foo,
						  'doesntexist')
		self.assertRaises(NotFound, self.folder1.unrestrictedTraverse,
						  'foo/doesntexist')
		self.assertRaises(AttributeError, getitem,
						  self.folder1.foo, 'isPrincipiaFolderish')
		self.assertRaises(NotFound, self.folder1.unrestrictedTraverse,
						  'foo/isPrincipiaFolderish/doesntexist')

	def test_traverseToNameStartingWithPlus(self):
		# Verify it's possible to traverse to a name such as +something
		assert_that(
			self.folder1.unrestrictedTraverse('+something'), is_('plus'))
