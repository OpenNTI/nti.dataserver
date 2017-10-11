#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

from nti.testing.matchers import validly_provides

import unittest

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import IContentFolder

from nti.contentfolder.model import RootFolder
from nti.contentfolder.model import ContentFolder

from nti.externalization.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.namedfile.file import NamedBlobFile as NamedFile

from nti.contentfolder.tests import SharedConfiguringTestLayer


class TestModel(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_interface(self):
        assert_that(ContentFolder(name=u"cc"), validly_provides(IContentFolder))
        assert_that(RootFolder(), validly_provides(IRootFolder))

    def test_container(self):
        root = RootFolder()
        f1 = root.add(ContentFolder(name=u'f1'))
        f1.add(NamedFile(name=u"foo"))
        assert_that('foo', is_in(f1))
        self.assertRaises(Exception, f1.__setitem__, 'foo', object())

        ext_obj = to_external_object(root)
        assert_that(ext_obj,
                    has_entries(
                        'MimeType', 'application/vnd.nextthought.contentrootfolder',
                        'name', 'root'))
        factory = find_factory_for(ext_obj)
        assert_that(factory, is_(none()))

        ext_obj = to_external_object(f1)
        assert_that(ext_obj,
                    has_entries(
                        'MimeType', 'application/vnd.nextthought.contentfolder',
                        'name', 'f1',
                        'filename', 'f1'))

        factory = find_factory_for(ext_obj)
        assert_that(factory, is_not(none()))
        internal = factory()
        update_from_external_object(internal, ext_obj)
        assert_that(internal, has_property('name', is_('f1')))
        assert_that(internal, has_property('filename', is_('f1')))

        del f1['foo']
        assert_that('foo', is_not(is_in(f1)))

    def test_move(self):
        root = RootFolder()
        bleach = root.add(ContentFolder(name=u'bleach'))
        ichigo = root.add(NamedFile(name=u"ichigo", data=b'shikai'))

        root.moveTo(ichigo, bleach, 'aizen')
        assert_that('ichigo', does_not(is_in(root)))
        assert_that('aizen', does_not(is_in(root)))
        assert_that('aizen', is_in(bleach))

        aizen = bleach['aizen']
        assert_that(aizen, has_property('__parent__', is_(bleach)))
        assert_that(aizen, has_property('data', is_(b'shikai')))

    def test_copy(self):
        root = RootFolder()
        bleach = root.add(ContentFolder(name=u'bleach'))
        ichigo = root.add(NamedFile(name=u"ichigo", data=b'shikai'))

        aizen = root.copyTo(ichigo, bleach, 'aizen')
        assert_that(aizen, is_not(none()))
        assert_that(aizen, is_not(ichigo))
        assert_that(aizen, has_property('data', is_(b'shikai')))

        same = root.copyTo(ichigo)
        assert_that(same, is_not(none()))
        assert_that(same, is_(ichigo))

        aizen = root.copyTo(ichigo, newName=u'aizen')
        assert_that(aizen, is_not(none()))
        assert_that(aizen, is_not(ichigo))
        assert_that(aizen, has_property('data', is_(b'shikai')))
