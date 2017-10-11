#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property

from nose.tools import assert_raises

import unittest

from nti.contentfolder.model import RootFolder
from nti.contentfolder.model import ContentFolder

from nti.contentfolder.utils import mkdirs
from nti.contentfolder.utils import traverse
from nti.contentfolder.utils import TraversalException

from nti.namedfile.file import NamedFile

from nti.contentfolder.tests import SharedConfiguringTestLayer


class TestUtils(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_traverse(self):
        root = RootFolder()
        root.add(ContentFolder(name=u'home')) \
            .add(ContentFolder(name=u'users')) \
            .add(ContentFolder(name=u'ichigo')) \
            .add(ContentFolder(name=u'bankai')) \
            .add(NamedFile(name=u'info.pdf'))
        assert_that(traverse(root), is_(root))
        assert_that(traverse(root, '/'), is_(root))
        assert_that(traverse(root, 'home'), has_property('name', 'home'))
        assert_that(traverse(root, '/home'), has_property('name', 'home'))

        with assert_raises(TraversalException):
            traverse(root, '/home/xxx')

        with assert_raises(TraversalException):
            traverse(root, '/home/users/uuu')

        pdf = traverse(root, '/home/users/ichigo/bankai/info.pdf')
        assert_that(pdf, has_property('name', 'info.pdf'))

        with assert_raises(TraversalException):
            traverse(root, '/home/users/ichigo/bankai/info.pdf/xyz')

        ichigo = traverse(root, '/home/.././home/users/./ichigo')
        assert_that(ichigo, has_property('name', 'ichigo'))

        obj = traverse(ichigo, 'bankai/info.pdf')
        assert_that(obj, is_(pdf))

        obj = traverse(ichigo, './bankai/..')
        assert_that(obj, is_(ichigo))

    def test_mkdirs(self):
        root = RootFolder()
        created = mkdirs(root, "/home/users/ichigo/bankai", ContentFolder)
        assert_that(created, has_property('name', 'bankai'))

        t = traverse(root, "/home/users/ichigo/bankai")
        assert_that(created, is_(t))

        created = mkdirs(root, "/home/users/ichigo/bankai", ContentFolder)
        assert_that(created, is_(t))
