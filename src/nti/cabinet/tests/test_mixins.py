#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_properties
does_not = is_not

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

import unittest

from nti.base.interfaces import DEFAULT_CONTENT_TYPE

from nti.cabinet.interfaces import ISource

from nti.cabinet.mixins import SourceFile
from nti.cabinet.mixins import SourceBucket

from nti.cabinet.tests import SharedConfiguringTestLayer


class TestMixins(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_source_bucket(self):
        bucket = SourceBucket(None, None)
        assert_that(bucket, has_properties('name', ''))
        bucket.name = u'bankai'
        assert_that(bucket, has_properties('__name__', 'bankai'))
        bucket.__name__ = '/usr/local/shikai'
        assert_that(bucket, has_properties('name', 'shikai'))

    def test_source_file(self):
        source = SourceFile(name=u'ichigo', path=u'/bankai', data=b'bleach')
        assert_that(source, validly_provides(ISource))
        assert_that(source, verifiably_provides(ISource))
        assert_that(source,
                    has_properties('name', is_('ichigo'),
                                   'data', is_(b'bleach'),
                                   'path', is_('/bankai'),
                                   'length', is_(6),
                                   'mode', is_('rb'),
                                   'filename', is_('/bankai/ichigo'),
                                   'contentType', is_(DEFAULT_CONTENT_TYPE),
                                   'lastModified', is_(not_none()),
                                   'createdTime', is_(not_none())))

        with source as fp:
            assert_that(fp.read(1), is_(b'b'))
            assert_that(fp.tell(), is_(1))
            fp.seek(3)
            assert_that(fp.read(2), is_(b'ac'))
