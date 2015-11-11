#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_in
from hamcrest import assert_that

from nti.testing.matchers import validly_provides

import unittest

from nti.contentfolder.model import RootFolder
from nti.contentfolder.model import ContentFolder

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import IContentFolder

from nti.contentfolder.tests import SharedConfiguringTestLayer

from nti.namedfile.file import NamedFile

class TestModel(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_interface(self):
		assert_that(ContentFolder(name="cc"), validly_provides(IContentFolder))
		assert_that(RootFolder(), validly_provides(IRootFolder))

	def test_container(self):
		root = RootFolder()
		f1 = root.append(ContentFolder(name='f1'))
		f1.append(NamedFile(name="foo"))
		assert_that('foo', is_in(f1))
		self.assertRaises(Exception, f1.__setitem__, 'foo', object())
