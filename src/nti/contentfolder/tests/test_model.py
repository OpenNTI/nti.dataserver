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
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import validly_provides

import unittest

from nti.contentfolder.model import RootFolder
from nti.contentfolder.model import ContentFolder

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import IContentFolder

from nti.externalization.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.namedfile.file import NamedFile

from nti.contentfolder.tests import SharedConfiguringTestLayer

class TestModel(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_interface(self):
		assert_that(ContentFolder(name="cc"), validly_provides(IContentFolder))
		assert_that(RootFolder(), validly_provides(IRootFolder))

	def test_container(self):
		root = RootFolder()
		f1 = root.add(ContentFolder(name='f1'))
		f1.add(NamedFile(name="foo"))
		assert_that('foo', is_in(f1))
		self.assertRaises(Exception, f1.__setitem__, 'foo', object())
		
		ext_obj = to_external_object(root)
		assert_that(ext_obj, 
					has_entries(
						u'MimeType', u'application/vnd.nextthought.contentrootfolder',
						u'name', u'root'))
		factory = find_factory_for(ext_obj)
		assert_that(factory, is_(none()))
		
		ext_obj = to_external_object(f1)
		assert_that(ext_obj, 
					has_entries(
						u'MimeType', u'application/vnd.nextthought.contentfolder',
						u'name', u'f1'))
		
		factory = find_factory_for(ext_obj)
		assert_that(factory, is_not(none()))
		internal = factory()
		update_from_external_object(internal, ext_obj)
		assert_that(internal, has_property('name', is_('f1')))
